"""
ChargeNexus EV Ecosystem Platform - Flask Backend
Multi-agent system powered by LangGraph + Anthropic Claude
"""

import os
import logging
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from routes.auth import auth_bp
from routes.landowner import landowner_bp
from routes.oem_sell import oem_sell_bp
from routes.oem_setup import oem_setup_bp
from routes.operator import operator_bp
from routes.driver import driver_bp
from routes.agent import agent_bp
from routes.marketplace import marketplace_bp
from routes.notifications import notif_bp
from routes.ocpp_mgmt import ocpp_bp
from routes.billing import billing_bp
from sse import sse_bp
from database import db, init_db

load_dotenv()


def create_app(env: str = None):
    app = Flask(__name__)
    env = env or os.getenv("FLASK_ENV", "development")
    is_prod = env == "production"

    # ── Logging ────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.WARNING if is_prod else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.setLevel(logging.WARNING if is_prod else logging.INFO)

    # ── Config ─────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "chargenexus-dev-secret-CHANGE-IN-PROD")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-CHANGE-IN-PROD")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///chargenexus.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    app.config["PROPAGATE_EXCEPTIONS"] = not is_prod

    # ── Extensions ─────────────────────────────────────────────────
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, origins=allowed_origins, supports_credentials=True)
    JWTManager(app)
    db.init_app(app)

    # ── Rate Limiter ───────────────────────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )
    # Tighter limits on auth endpoints
    limiter.limit("10 per minute")(auth_bp)

    # ── Blueprints ─────────────────────────────────────────────────
    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(landowner_bp,   url_prefix="/api/landowner")
    app.register_blueprint(oem_sell_bp,    url_prefix="/api/oem-sell")
    app.register_blueprint(oem_setup_bp,   url_prefix="/api/oem-setup")
    app.register_blueprint(operator_bp,    url_prefix="/api/operator")
    app.register_blueprint(driver_bp,      url_prefix="/api/driver")
    app.register_blueprint(agent_bp,       url_prefix="/api/agent")
    app.register_blueprint(marketplace_bp, url_prefix="/api/marketplace")
    app.register_blueprint(notif_bp,       url_prefix="/api/notifications")
    app.register_blueprint(ocpp_bp,        url_prefix="/api/ocpp")
    app.register_blueprint(billing_bp,     url_prefix="/api/billing")
    app.register_blueprint(sse_bp,         url_prefix="/api/sse")

    with app.app_context():
        init_db()

    # ── JWT Refresh endpoint ────────────────────────────────────────
    @app.route("/api/auth/refresh", methods=["POST"])
    @jwt_required(refresh=True)
    def refresh_token():
        user_id = get_jwt_identity()
        new_token = create_access_token(identity=user_id)
        return jsonify({"token": new_token})

    # ── Global error handlers ───────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Unprocessable entity", "details": str(e)}), 422

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"error": "Too many requests — please slow down"}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error("500 error: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

    # ── Health check ────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "platform": "ChargeNexus v1.0", "env": env})

    return app

app = create_app()
if __name__ == "__main__":
    # app = create_app()
    debug = os.getenv("FLASK_ENV", "development") != "production"
    # threaded=True is required for SSE — each client holds a long-lived connection
    # app.run(debug=debug, port=int(os.getenv("PORT", 5000)), threaded=True)

    # Render injects PORT env var — must bind 0.0.0.0 (not localhost)
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port, threaded=True)