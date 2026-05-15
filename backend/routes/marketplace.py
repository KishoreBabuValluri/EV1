"""Marketplace routes — public listings for cross-stakeholder discovery."""
from flask import Blueprint, request, jsonify
from database import LandListing, ChargerProduct, ChargingStation

marketplace_bp = Blueprint("marketplace", __name__)

@marketplace_bp.route("/land-listings", methods=["GET"])
def land_listings():
    city = request.args.get("city")
    loc_type = request.args.get("location_type")
    q = LandListing.query.filter_by(status="active")
    if city:
        q = q.filter_by(city=city)
    if loc_type:
        q = q.filter_by(location_type=loc_type)
    return jsonify([l.to_dict() for l in q.order_by(LandListing.ai_score.desc()).limit(50).all()])

@marketplace_bp.route("/charger-products", methods=["GET"])
def charger_products():
    ctype = request.args.get("charger_type")
    min_kw = request.args.get("min_kw", type=float)
    max_price = request.args.get("max_price", type=float)
    q = ChargerProduct.query.filter_by(status="active")
    if ctype:
        q = q.filter_by(charger_type=ctype)
    if min_kw:
        q = q.filter(ChargerProduct.power_kw >= min_kw)
    if max_price:
        q = q.filter(ChargerProduct.unit_price <= max_price)
    return jsonify([p.to_dict() for p in q.order_by(ChargerProduct.power_kw.desc()).limit(50).all()])

@marketplace_bp.route("/charging-stations", methods=["GET"])
def charging_stations():
    city = request.args.get("city")
    q = ChargingStation.query.filter_by(status="active")
    if city:
        q = q.filter_by(city=city)
    return jsonify([s.to_dict() for s in q.all()])

@marketplace_bp.route("/stats", methods=["GET"])
def platform_stats():
    return jsonify({
        "total_land_listings": LandListing.query.filter_by(status="active").count(),
        "total_charger_products": ChargerProduct.query.filter_by(status="active").count(),
        "total_stations": ChargingStation.query.filter_by(status="active").count(),
        "cities_covered": ["Hyderabad", "Warangal", "Vijayawada", "Bengaluru"],
    })
