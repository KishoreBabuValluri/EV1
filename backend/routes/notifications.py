"""Notification routes — in-app bell system."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, Notification

notif_bp = Blueprint("notifications", __name__)


@notif_bp.route("", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    unread_only = request.args.get("unread", "false").lower() == "true"

    q = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)
    q = q.order_by(Notification.created_at.desc())

    paginated = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "notifications": [n.to_dict() for n in paginated.items],
        "unread_count": Notification.query.filter_by(user_id=user_id, is_read=False).count(),
        "total": paginated.total,
        "pages": paginated.pages,
        "page": page,
    })


@notif_bp.route("/<int:nid>/read", methods=["POST"])
@jwt_required()
def mark_read(nid):
    user_id = int(get_jwt_identity())
    notif = Notification.query.filter_by(id=nid, user_id=user_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@notif_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})


@notif_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def unread_count():
    user_id = int(get_jwt_identity())
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({"unread_count": count})
