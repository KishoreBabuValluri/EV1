"""OEM Sell routes — charger product listings, orders, analytics."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, User, ChargerProduct, ChargerOrder

oem_sell_bp = Blueprint("oem_sell", __name__)

@oem_sell_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    user_id = int(get_jwt_identity())
    products = ChargerProduct.query.filter_by(oem_id=user_id).all()
    return jsonify([p.to_dict() for p in products])

@oem_sell_bp.route("/products", methods=["POST"])
@jwt_required()
def add_product():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    product = ChargerProduct(
        oem_id=user_id,
        model_name=data.get("model_name"), power_kw=data.get("power_kw"),
        charger_type=data.get("charger_type"), connector_standard=data.get("connector_standard"),
        unit_price=data.get("unit_price"), stock_available=data.get("stock_available", 0),
        warranty_years=data.get("warranty_years"), description=data.get("description"),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201

@oem_sell_bp.route("/products/<int:pid>", methods=["PUT"])
@jwt_required()
def update_product(pid):
    user_id = int(get_jwt_identity())
    product = ChargerProduct.query.filter_by(id=pid, oem_id=user_id).first_or_404()
    data = request.get_json()
    for field in ["model_name","power_kw","charger_type","connector_standard","unit_price","stock_available","warranty_years","description","status"]:
        if field in data:
            setattr(product, field, data[field])
    db.session.commit()
    return jsonify(product.to_dict())

@oem_sell_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())
    products = ChargerProduct.query.filter_by(oem_id=user_id).all()
    pids = [p.id for p in products]
    orders = ChargerOrder.query.filter(ChargerOrder.product_id.in_(pids)).order_by(ChargerOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])

@oem_sell_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    products = ChargerProduct.query.filter_by(oem_id=user_id).all()
    pids = [p.id for p in products]
    orders = ChargerOrder.query.filter(ChargerOrder.product_id.in_(pids)).all()
    return jsonify({
        "total_products": len(products),
        "total_orders": len(orders),
        "total_revenue": sum(o.total_amount for o in orders if o.total_amount),
        "total_units_sold": sum(o.quantity for o in orders),
    })
