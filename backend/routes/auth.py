"""Auth routes — register, login, logout for all 5 stakeholder roles."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database import db, User

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = ["landowner", "oem_sell", "oem_setup", "operator", "driver"]


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    role = data.get("role", "")

    if not email or not password or role not in VALID_ROLES:
        return jsonify({"error": "Invalid registration data or role"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        email=email,
        role=role,
        full_name=data.get("full_name", ""),
        phone=data.get("phone", ""),
        company=data.get("company", ""),
        city=data.get("city", ""),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())


@auth_bp.route("/demo-login", methods=["POST"])
def demo_login():
    """Quick login with demo credentials for each role."""
    role = request.get_json().get("role")
    demo_emails = {
        "landowner": "landowner@demo.com",
        "oem_sell": "oemsell@demo.com",
        "oem_setup": "oemsetup@demo.com",
        "operator": "operator@demo.com",
        "driver": "driver@demo.com",
    }
    email = demo_emails.get(role)
    if not email:
        return jsonify({"error": "Invalid role"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Demo user not found"}), 404
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh_placeholder():
    """Handled at app level via /api/auth/refresh with refresh=True JWT."""
    from flask import jsonify
    return jsonify({"error": "Use POST /api/auth/refresh with refresh token in Authorization header"}), 400
