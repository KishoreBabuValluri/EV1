"""OEM Setup routes — site matching, lease requests with notification."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, LandListing, LeaseRequest, User, push_notification

oem_setup_bp = Blueprint("oem_setup", __name__)


@oem_setup_bp.route("/available-sites", methods=["GET"])
@jwt_required()
def available_sites():
    city = request.args.get("city")
    min_area = request.args.get("min_area", 0, type=int)
    loc_type = request.args.get("location_type")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    q = LandListing.query.filter_by(status="active")
    if city:
        q = q.filter(LandListing.city.ilike(f"%{city}%"))
    if min_area:
        q = q.filter(LandListing.area_sqft >= min_area)
    if loc_type:
        q = q.filter_by(location_type=loc_type)

    paginated = q.order_by(LandListing.ai_score.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "listings": [l.to_dict() for l in paginated.items],
        "total": paginated.total,
        "page": page,
    })


@oem_setup_bp.route("/send-lease-request", methods=["POST"])
@jwt_required()
def send_lease_request():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    listing_id = data.get("listing_id")
    offered = data.get("offered_monthly")
    term = data.get("lease_term_years")
    message = (data.get("message") or "").strip()[:2000]

    if not listing_id:
        return jsonify({"error": "listing_id required"}), 422
    try:
        offered = float(offered) if offered is not None else None
        term = int(term) if term is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "offered_monthly and lease_term_years must be numbers"}), 422

    listing = LandListing.query.get_or_404(listing_id)
    requester = User.query.get(user_id)

    req = LeaseRequest(
        listing_id=listing_id, requester_id=user_id,
        offered_monthly=offered, lease_term_years=term, message=message,
    )
    db.session.add(req)
    db.session.flush()

    # Notify the land owner
    push_notification(
        user_id=listing.owner_id,
        title="New lease request received",
        body=f"{requester.full_name} ({requester.company or 'individual'}) offered ₹{offered:,.0f}/mo for '{listing.title}'.",
        notif_type="lease_request",
        entity_id=req.id,
    )
    db.session.commit()
    return jsonify(req.to_dict()), 201


@oem_setup_bp.route("/my-requests", methods=["GET"])
@jwt_required()
def my_requests():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    paginated = (LeaseRequest.query
                 .filter_by(requester_id=user_id)
                 .order_by(LeaseRequest.created_at.desc())
                 .paginate(page=page, per_page=20, error_out=False))
    return jsonify({
        "requests": [r.to_dict() for r in paginated.items],
        "total": paginated.total,
    })
