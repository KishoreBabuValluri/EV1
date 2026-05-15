"""
Driver routes — stations, sessions, wallet with Razorpay payment.
"""
import os
import hmac
import hashlib
import math
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, ChargingStation, ChargingSession, DriverWallet, WalletTransaction, User
from sse import broadcast_availability          # SSE broadcast helper

driver_bp = Blueprint("driver", __name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_or_create_wallet(user_id):
    w = DriverWallet.query.filter_by(driver_id=user_id).first()
    if not w:
        w = DriverWallet(driver_id=user_id, balance=0.0, reward_points=0)
        db.session.add(w)
        db.session.flush()
    return w


def _razorpay_client():
    import razorpay
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env")
    return razorpay.Client(auth=(key_id, key_secret))


# ── stations ───────────────────────────────────────────────────────────────────

@driver_bp.route("/stations/nearby", methods=["GET"])
def nearby_stations():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 15, type=float)
    stations = ChargingStation.query.filter_by(status="active").all()
    result = []
    for s in stations:
        if lat and lon and s.latitude and s.longitude:
            dist = _distance_km(lat, lon, s.latitude, s.longitude)
            if dist <= radius:
                d = s.to_dict()
                d["distance_km"] = round(dist, 1)
                result.append(d)
        else:
            result.append(s.to_dict())
    result.sort(key=lambda x: x.get("distance_km", 999))
    return jsonify(result)


# ── sessions ───────────────────────────────────────────────────────────────────

@driver_bp.route("/sessions", methods=["GET"])
@jwt_required()
def sessions():
    user_id = int(get_jwt_identity())
    sess = (ChargingSession.query
            .filter_by(driver_id=user_id)
            .order_by(ChargingSession.start_time.desc())
            .limit(50).all())
    return jsonify([s.to_dict() for s in sess])


@driver_bp.route("/sessions/start", methods=["POST"])
@jwt_required()
def start_session():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    station = ChargingStation.query.get_or_404(data.get("station_id"))
    session = ChargingSession(
        driver_id=user_id, station_id=station.id,
        start_time=datetime.utcnow(), status="active",
        payment_method=data.get("payment_method", "Wallet"),
    )
    if station.available_points > 0:
        station.available_points -= 1
    db.session.add(session)
    db.session.commit()
    # Broadcast availability change via SSE
    broadcast_availability(station.id, station.available_points, station.total_points)
    return jsonify(session.to_dict()), 201


@driver_bp.route("/sessions/<int:sid>/end", methods=["POST"])
@jwt_required()
def end_session(sid):
    user_id = int(get_jwt_identity())
    session = ChargingSession.query.filter_by(id=sid, driver_id=user_id).first_or_404()
    data = request.get_json() or {}
    session.end_time = datetime.utcnow()
    session.energy_kwh = max(0, float(data.get("energy_kwh", 0)))
    station = ChargingStation.query.get(session.station_id)
    price = station.price_per_kwh if station else 40
    session.amount_inr = round(session.energy_kwh * price, 2)
    session.status = "completed"
    if station:
        station.available_points = min(station.total_points, station.available_points + 1)

    wallet = _get_or_create_wallet(user_id)
    wallet.reward_points += int(session.energy_kwh * 2)
    wallet.balance = round(wallet.balance - session.amount_inr, 2)

    # Record debit transaction
    db.session.add(WalletTransaction(
        driver_id=user_id, amount=-session.amount_inr,
        txn_type="debit", status="success",
        notes=f"Charging session at {station.name if station else 'Unknown'}"
    ))
    db.session.commit()

    if station:
        broadcast_availability(station.id, station.available_points, station.total_points)
    return jsonify(session.to_dict())


# ── wallet ─────────────────────────────────────────────────────────────────────

@driver_bp.route("/wallet", methods=["GET"])
@jwt_required()
def wallet():
    user_id = int(get_jwt_identity())
    w = _get_or_create_wallet(user_id)
    db.session.commit()
    return jsonify(w.to_dict())


@driver_bp.route("/wallet/transactions", methods=["GET"])
@jwt_required()
def wallet_transactions():
    user_id = int(get_jwt_identity())
    txns = (WalletTransaction.query
            .filter_by(driver_id=user_id)
            .order_by(WalletTransaction.created_at.desc())
            .limit(20).all())
    return jsonify([t.to_dict() for t in txns])


# ── Razorpay payment flow ──────────────────────────────────────────────────────

@driver_bp.route("/wallet/create-order", methods=["POST"])
@jwt_required()
def create_order():
    """
    Step 1: Create a Razorpay order.
    Client sends { amount: 500 } (INR integer).
    Returns { order_id, amount, currency, key_id } to frontend.
    Frontend loads Razorpay checkout with order_id.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    amount_inr = data.get("amount")

    # Validate
    try:
        amount_inr = int(amount_inr)
        if amount_inr < 10 or amount_inr > 100000:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be an integer between 10 and 100000 (INR)"}), 422

    user = User.query.get(user_id)

    try:
        client = _razorpay_client()
    except RuntimeError as e:
        # Dev fallback — return mock order so UI can be tested without Razorpay keys
        current_app.logger.warning("Razorpay not configured — using dev mock: %s", e)
        mock_order_id = f"order_DEV_{user_id}_{int(datetime.utcnow().timestamp())}"
        txn = WalletTransaction(
            driver_id=user_id, amount=amount_inr, txn_type="topup",
            status="pending", razorpay_order_id=mock_order_id,
            notes="Dev mock order"
        )
        db.session.add(txn)
        db.session.commit()
        return jsonify({
            "order_id": mock_order_id,
            "amount": amount_inr * 100,
            "currency": "INR",
            "key_id": "rzp_test_DEV_MOCK",
            "prefill": {"name": user.full_name, "email": user.email, "contact": user.phone or ""},
            "is_mock": True,
        })

    order = client.order.create({
        "amount": amount_inr * 100,   # Razorpay expects paise
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"user_id": str(user_id), "platform": "ChargeNexus"},
    })

    # Persist pending transaction
    txn = WalletTransaction(
        driver_id=user_id, amount=amount_inr, txn_type="topup",
        status="pending", razorpay_order_id=order["id"],
        notes=f"Wallet topup ₹{amount_inr}"
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": os.getenv("RAZORPAY_KEY_ID"),
        "prefill": {
            "name": user.full_name or "",
            "email": user.email,
            "contact": user.phone or "",
        },
    })


@driver_bp.route("/wallet/verify-payment", methods=["POST"])
@jwt_required()
def verify_payment():
    """
    Step 2: Verify Razorpay signature and credit wallet.
    Client sends { razorpay_order_id, razorpay_payment_id, razorpay_signature }.
    Returns updated wallet.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    order_id = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature = data.get("razorpay_signature", "")

    # Find the pending transaction
    txn = WalletTransaction.query.filter_by(
        driver_id=user_id,
        razorpay_order_id=order_id,
        status="pending"
    ).first()

    if not txn:
        return jsonify({"error": "Transaction not found or already processed"}), 404

    # Dev mock — skip HMAC check
    is_mock = order_id.startswith("order_DEV_")

    if not is_mock:
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        if not key_secret:
            return jsonify({"error": "Server not configured for payments"}), 500

        # HMAC-SHA256 verification
        body = f"{order_id}|{payment_id}"
        expected = hmac.new(
            key_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            txn.status = "failed"
            db.session.commit()
            return jsonify({"error": "Payment signature verification failed"}), 400

    # Credit wallet
    txn.status = "success"
    txn.razorpay_payment_id = payment_id
    txn.razorpay_signature = signature

    wallet = _get_or_create_wallet(user_id)
    wallet.balance = round(wallet.balance + txn.amount, 2)
    db.session.commit()

    return jsonify({
        "success": True,
        "credited": txn.amount,
        "wallet": wallet.to_dict(),
    })


# ── stats ──────────────────────────────────────────────────────────────────────

@driver_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    completed = ChargingSession.query.filter_by(driver_id=user_id, status="completed").all()
    wallet = DriverWallet.query.filter_by(driver_id=user_id).first()
    return jsonify({
        "total_sessions": len(completed),
        "total_energy_kwh": round(sum(s.energy_kwh for s in completed if s.energy_kwh), 1),
        "total_spent_inr": round(sum(s.amount_inr for s in completed if s.amount_inr), 0),
        "wallet_balance": round(wallet.balance, 2) if wallet else 0,
        "reward_points": wallet.reward_points if wallet else 0,
    })
