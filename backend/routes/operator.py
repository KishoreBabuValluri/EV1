"""Operator routes — stations, charger points, revenue charts, sessions."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, ChargingStation, ChargingSession, ChargerPoint
from datetime import datetime, timedelta
from sqlalchemy import func
from sse import broadcast_availability, broadcast_point_status

operator_bp = Blueprint("operator", __name__)


@operator_bp.route("/stations", methods=["GET"])
@jwt_required()
def get_stations():
    user_id = int(get_jwt_identity())
    stations = ChargingStation.query.filter_by(operator_id=user_id).all()
    return jsonify([s.to_dict() for s in stations])


@operator_bp.route("/stations", methods=["POST"])
@jwt_required()
def add_station():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    total_pts = data.get("total_points", 0)
    station = ChargingStation(
        operator_id=user_id,
        name=data.get("name"), address=data.get("address"), city=data.get("city"),
        latitude=data.get("latitude"), longitude=data.get("longitude"),
        total_points=total_pts, available_points=total_pts,
        price_per_kwh=data.get("price_per_kwh"),
        land_listing_id=data.get("land_listing_id"),
        amenities=",".join(data.get("amenities", [])),
    )
    db.session.add(station)
    db.session.flush()

    # Auto-create ChargerPoint rows for each bay
    connector = data.get("connector_type", "CCS2")
    power = data.get("power_kw", 60)
    for i in range(1, total_pts + 1):
        db.session.add(ChargerPoint(
            station_id=station.id, point_number=i,
            connector_type=connector, power_kw=power, status="available",
        ))
    db.session.commit()
    return jsonify(station.to_dict()), 201


@operator_bp.route("/stations/<int:sid>", methods=["PUT"])
@jwt_required()
def update_station(sid):
    user_id = int(get_jwt_identity())
    station = ChargingStation.query.filter_by(id=sid, operator_id=user_id).first_or_404()
    data = request.get_json()
    for field in ["name","address","city","total_points","available_points","price_per_kwh","status","uptime_percent"]:
        if field in data:
            setattr(station, field, data[field])
    db.session.commit()
    return jsonify(station.to_dict())


@operator_bp.route("/stations/<int:sid>/charger-points", methods=["GET"])
@jwt_required()
def get_charger_points(sid):
    user_id = int(get_jwt_identity())
    station = ChargingStation.query.filter_by(id=sid, operator_id=user_id).first_or_404()
    points = ChargerPoint.query.filter_by(station_id=station.id).order_by(ChargerPoint.point_number).all()
    return jsonify([p.to_dict() for p in points])


@operator_bp.route("/stations/<int:sid>/charger-points/<int:pid>", methods=["PUT"])
@jwt_required()
def update_charger_point(sid, pid):
    user_id = int(get_jwt_identity())
    station = ChargingStation.query.filter_by(id=sid, operator_id=user_id).first_or_404()
    point = ChargerPoint.query.filter_by(id=pid, station_id=station.id).first_or_404()
    data = request.get_json()
    for field in ["status", "fault_code", "connector_type", "power_kw"]:
        if field in data:
            setattr(point, field, data[field])
    point.last_heartbeat = datetime.utcnow()
    # Sync station available_points counter
    available = ChargerPoint.query.filter_by(station_id=station.id, status="available").count()
    station.available_points = available
    db.session.commit()
    # Broadcast to all SSE clients
    broadcast_point_status(station.id, point.id, point.status, available, station.total_points)
    return jsonify(point.to_dict())


@operator_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    stations = ChargingStation.query.filter_by(operator_id=user_id).all()
    sids = [s.id for s in stations]
    sessions = ChargingSession.query.filter(ChargingSession.station_id.in_(sids)).all()
    return jsonify({
        "total_stations": len(stations),
        "total_points": sum(s.total_points for s in stations),
        "available_points": sum(s.available_points for s in stations),
        "total_sessions": len(sessions),
        "total_energy_kwh": round(sum(s.energy_kwh for s in sessions if s.energy_kwh), 1),
        "total_revenue_inr": round(sum(s.amount_inr for s in sessions if s.amount_inr), 2),
        "avg_uptime_pct": round(sum(s.uptime_percent for s in stations) / len(stations), 1) if stations else 0,
    })


@operator_bp.route("/revenue-chart", methods=["GET"])
@jwt_required()
def revenue_chart():
    """Return daily revenue + session count for the last N days (default 30)."""
    user_id = int(get_jwt_identity())
    days = request.args.get("days", 30, type=int)
    stations = ChargingStation.query.filter_by(operator_id=user_id).all()
    sids = [s.id for s in stations]
    if not sids:
        return jsonify([])

    since = datetime.utcnow() - timedelta(days=days)

    # Group sessions by date and station
    rows = (
        db.session.query(
            func.date(ChargingSession.start_time).label("day"),
            ChargingStation.name.label("station"),
            func.count(ChargingSession.id).label("sessions"),
            func.sum(ChargingSession.amount_inr).label("revenue"),
            func.sum(ChargingSession.energy_kwh).label("energy"),
        )
        .join(ChargingStation, ChargingSession.station_id == ChargingStation.id)
        .filter(
            ChargingSession.station_id.in_(sids),
            ChargingSession.start_time >= since,
            ChargingSession.status == "completed",
        )
        .group_by(func.date(ChargingSession.start_time), ChargingStation.name)
        .order_by(func.date(ChargingSession.start_time))
        .all()
    )

    # Aggregate totals per day (for line chart) + per station (for bar chart)
    daily = {}
    for row in rows:
        day_str = str(row.day)
        if day_str not in daily:
            daily[day_str] = {"date": day_str, "revenue": 0, "sessions": 0, "energy": 0}
        daily[day_str]["revenue"] += round(float(row.revenue or 0), 2)
        daily[day_str]["sessions"] += int(row.sessions or 0)
        daily[day_str]["energy"] += round(float(row.energy or 0), 1)

    # Utilization per station (sessions / capacity)
    station_util = {}
    for row in rows:
        name = row.station
        if name not in station_util:
            station_util[name] = {"station": name, "sessions": 0, "revenue": 0}
        station_util[name]["sessions"] += int(row.sessions or 0)
        station_util[name]["revenue"] += round(float(row.revenue or 0), 2)

    return jsonify({
        "daily": sorted(daily.values(), key=lambda x: x["date"]),
        "by_station": list(station_util.values()),
    })


@operator_bp.route("/sessions", methods=["GET"])
@jwt_required()
def sessions():
    user_id = int(get_jwt_identity())
    stations = ChargingStation.query.filter_by(operator_id=user_id).all()
    sids = [s.id for s in stations]
    sess = (ChargingSession.query
            .filter(ChargingSession.station_id.in_(sids))
            .order_by(ChargingSession.start_time.desc())
            .limit(50).all())
    return jsonify([s.to_dict() for s in sess])
