"""
Billing routes — credit purchase, subscription, usage stats.

GET  /api/billing/plans               available plans + prices for this user's role
GET  /api/billing/credit-packs        available credit packs to purchase
GET  /api/billing/wallet              current credit balance + stats
GET  /api/billing/transactions        credit transaction history
POST /api/billing/create-credit-order Razorpay order for credit pack purchase
POST /api/billing/verify-credit-order Verify + credit wallet
POST /api/billing/create-sub-order    Razorpay order for subscription
POST /api/billing/verify-sub-order    Verify + activate subscription
"""

import os
import hmac
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, User, CreditWallet, CreditTransaction, Subscription, NlpUsage
from credits import (
    PLANS, CREDIT_PACKS, LLM_CREDIT_COST,
    get_plan_price, get_monthly_credits, get_nlp_daily_limit,
    credit_credits, activate_subscription,
)

billing_bp = Blueprint("billing", __name__)


def _razorpay_client():
    import razorpay
    key_id     = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise RuntimeError("RAZORPAY keys not configured")
    return razorpay.Client(auth=(key_id, key_secret))


def _verify_hmac(order_id: str, payment_id: str, signature: str) -> bool:
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not secret:
        return True  # dev mode — skip verification
    body     = f"{order_id}|{payment_id}"
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Plan info ─────────────────────────────────────────────────────────────────

@billing_bp.route("/plans", methods=["GET"])
@jwt_required()
def plans():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    role = user.role
    result = []
    for plan_id, plan_data in PLANS.items():
        price     = get_plan_price(plan_id, role)
        credits_m = get_monthly_credits(plan_id, role)
        nlp_limit = get_nlp_daily_limit(plan_id, role)
        result.append({
            "id":               plan_id,
            "name":             plan_data["name"],
            "price_inr":        price,
            "credits_per_month": credits_m,
            "nlp_daily_limit":  nlp_limit if nlp_limit != -1 else "Unlimited",
            "llm_cost_per_query": LLM_CREDIT_COST.get(role, 5),
            "features":         plan_data["features"],
            "is_current":       user.plan == plan_id,
        })
    return jsonify({
        "plans": result,
        "current_plan": user.plan,
        "role": role,
    })


@billing_bp.route("/credit-packs", methods=["GET"])
@jwt_required()
def credit_packs():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    role = user.role if user else "driver"
    cost_per_query = LLM_CREDIT_COST.get(role, 5)
    packs = []
    for p in CREDIT_PACKS:
        queries = p["credits"] // cost_per_query
        packs.append({**p, "queries_for_your_role": queries})
    return jsonify({"packs": packs, "cost_per_query": cost_per_query})


# ── Credit wallet info ────────────────────────────────────────────────────────

@billing_bp.route("/wallet", methods=["GET"])
@jwt_required()
def wallet():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    cw      = CreditWallet.query.filter_by(user_id=user_id).first()
    today   = datetime.utcnow().strftime("%Y-%m-%d")
    nlp_today = NlpUsage.query.filter_by(user_id=user_id, date=today).first()
    nlp_limit = get_nlp_daily_limit(user.plan if user else "free", user.role if user else "driver")

    return jsonify({
        "credits": cw.to_dict() if cw else {"balance": 0, "lifetime_earned": 0, "lifetime_spent": 0},
        "plan": user.plan if user else "free",
        "plan_expires_at": user.plan_expires_at.isoformat() if user and user.plan_expires_at else None,
        "nlp_used_today": nlp_today.count if nlp_today else 0,
        "nlp_limit_today": nlp_limit if nlp_limit != -1 else None,
        "llm_cost_per_query": LLM_CREDIT_COST.get(user.role, 5) if user else 5,
    })


@billing_bp.route("/transactions", methods=["GET"])
@jwt_required()
def transactions():
    user_id = int(get_jwt_identity())
    page    = request.args.get("page", 1, type=int)
    txns    = (CreditTransaction.query
               .filter_by(user_id=user_id)
               .order_by(CreditTransaction.created_at.desc())
               .paginate(page=page, per_page=20, error_out=False))
    return jsonify({
        "transactions": [t.to_dict() for t in txns.items],
        "total": txns.total,
        "page": page,
    })


# ── Credit pack purchase ──────────────────────────────────────────────────────

@billing_bp.route("/create-credit-order", methods=["POST"])
@jwt_required()
def create_credit_order():
    user_id  = int(get_jwt_identity())
    data     = request.get_json() or {}
    pack_id  = data.get("pack_id")
    pack     = next((p for p in CREDIT_PACKS if p["id"] == pack_id), None)
    if not pack:
        return jsonify({"error": f"Unknown pack_id: {pack_id}"}), 422

    try:
        client = _razorpay_client()
        order  = client.order.create({
            "amount":          pack["price_inr"] * 100,
            "currency":        "INR",
            "payment_capture": 1,
            "notes": {"user_id": str(user_id), "pack_id": pack_id, "credits": pack["credits"]},
        })
        order_id = order["id"]
    except RuntimeError:
        # Dev mock
        order_id = f"order_CREDIT_DEV_{user_id}_{pack_id}"
        current_app.logger.warning("Razorpay not configured — using dev mock")

    user = User.query.get(user_id)
    return jsonify({
        "order_id":  order_id,
        "amount":    pack["price_inr"] * 100,
        "currency":  "INR",
        "key_id":    os.getenv("RAZORPAY_KEY_ID", "rzp_test_DEV"),
        "pack":      pack,
        "is_mock":   order_id.startswith("order_CREDIT_DEV"),
        "prefill":   {"name": user.full_name if user else "", "email": user.email if user else ""},
    })


@billing_bp.route("/verify-credit-order", methods=["POST"])
@jwt_required()
def verify_credit_order():
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}
    order_id   = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature  = data.get("razorpay_signature", "")
    pack_id    = data.get("pack_id")

    pack = next((p for p in CREDIT_PACKS if p["id"] == pack_id), None)
    if not pack:
        return jsonify({"error": "Unknown pack"}), 422

    is_mock = order_id.startswith("order_CREDIT_DEV")
    if not is_mock and not _verify_hmac(order_id, payment_id, signature):
        return jsonify({"error": "Payment signature verification failed"}), 400

    new_balance = credit_credits(
        user_id=user_id,
        amount=pack["credits"],
        txn_type="purchase",
        description=f"Purchased {pack['credits']} credits ({pack['label']} pack) · ₹{pack['price_inr']}",
        reference_id=payment_id or order_id,
    )
    return jsonify({"success": True, "credits_added": pack["credits"], "new_balance": new_balance})


# ── Subscription purchase ─────────────────────────────────────────────────────

@billing_bp.route("/create-sub-order", methods=["POST"])
@jwt_required()
def create_sub_order():
    user_id  = int(get_jwt_identity())
    data     = request.get_json() or {}
    plan     = data.get("plan")
    if plan not in ("pro", "business"):
        return jsonify({"error": "plan must be pro or business"}), 422

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    price_inr = get_plan_price(plan, user.role)
    credits_m = get_monthly_credits(plan, user.role)

    try:
        client = _razorpay_client()
        order  = client.order.create({
            "amount":          price_inr * 100,
            "currency":        "INR",
            "payment_capture": 1,
            "notes": {"user_id": str(user_id), "plan": plan, "role": user.role},
        })
        order_id = order["id"]
    except RuntimeError:
        order_id = f"order_SUB_DEV_{user_id}_{plan}"
        current_app.logger.warning("Razorpay not configured — using dev mock for subscription")

    return jsonify({
        "order_id":       order_id,
        "amount":         price_inr * 100,
        "currency":       "INR",
        "key_id":         os.getenv("RAZORPAY_KEY_ID", "rzp_test_DEV"),
        "plan":           plan,
        "price_inr":      price_inr,
        "credits_per_month": credits_m,
        "is_mock":        order_id.startswith("order_SUB_DEV"),
        "prefill":        {"name": user.full_name, "email": user.email},
    })


@billing_bp.route("/verify-sub-order", methods=["POST"])
@jwt_required()
def verify_sub_order():
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}
    order_id   = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature  = data.get("razorpay_signature", "")
    plan       = data.get("plan")

    if plan not in ("pro", "business"):
        return jsonify({"error": "Invalid plan"}), 422

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    is_mock = order_id.startswith("order_SUB_DEV")
    if not is_mock and not _verify_hmac(order_id, payment_id, signature):
        return jsonify({"error": "Payment signature verification failed"}), 400

    result = activate_subscription(
        user_id=user_id,
        role=user.role,
        plan=plan,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id or order_id,
    )
    return jsonify({"success": True, **result})
