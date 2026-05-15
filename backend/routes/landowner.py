"""Land owner routes — listings, lease requests, stats."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, User, LandListing, LeaseRequest, push_notification

landowner_bp = Blueprint("landowner", __name__)


def _validate_listing(data):
    errors = []
    if not data.get("title") or len(data.get("title", "")) > 200:
        errors.append("title is required (max 200 chars)")
    if data.get("area_sqft") is not None:
        try:
            a = int(data["area_sqft"])
            if a <= 0 or a > 10_000_000:
                errors.append("area_sqft must be 1–10,000,000")
        except (ValueError, TypeError):
            errors.append("area_sqft must be a number")
    if data.get("monthly_lease") is not None:
        try:
            l = float(data["monthly_lease"])
            if l < 0 or l > 100_000_000:
                errors.append("monthly_lease out of range")
        except (ValueError, TypeError):
            errors.append("monthly_lease must be a number")
    return errors


@landowner_bp.route("/listings", methods=["GET"])
@jwt_required()
def get_listings():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    paginated = (LandListing.query
                 .filter_by(owner_id=user_id)
                 .order_by(LandListing.created_at.desc())
                 .paginate(page=page, per_page=per_page, error_out=False))
    return jsonify({
        "listings": [l.to_dict() for l in paginated.items],
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
    })


@landowner_bp.route("/listings/all", methods=["GET"])
@jwt_required()
def get_all_listings():
    """Lightweight full list for map view (no pagination)."""
    user_id = int(get_jwt_identity())
    listings = LandListing.query.filter_by(owner_id=user_id).all()
    return jsonify([l.to_dict() for l in listings])


@landowner_bp.route("/listings", methods=["POST"])
@jwt_required()
def add_listing():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    errors = _validate_listing(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    listing = LandListing(
        owner_id=user_id,
        title=data.get("title").strip(),
        address=data.get("address", "").strip()[:300],
        city=data.get("city", "").strip()[:80],
        state=data.get("state", "Telangana").strip()[:80],
        area_sqft=int(data["area_sqft"]) if data.get("area_sqft") else None,
        location_type=data.get("location_type"),
        monthly_lease=float(data["monthly_lease"]) if data.get("monthly_lease") else None,
        power_availability=data.get("power_availability", "").strip()[:100],
        daily_traffic=int(data["daily_traffic"]) if data.get("daily_traffic") else None,
        description=data.get("description", "").strip()[:2000],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    db.session.add(listing)
    db.session.commit()
    return jsonify(listing.to_dict()), 201


@landowner_bp.route("/listings/<int:lid>", methods=["PUT"])
@jwt_required()
def update_listing(lid):
    user_id = int(get_jwt_identity())
    listing = LandListing.query.filter_by(id=lid, owner_id=user_id).first_or_404()
    data = request.get_json() or {}
    errors = _validate_listing(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422
    for field in ["title", "address", "city", "area_sqft", "location_type",
                  "monthly_lease", "power_availability", "daily_traffic", "description", "status"]:
        if field in data:
            setattr(listing, field, data[field])
    db.session.commit()
    return jsonify(listing.to_dict())


@landowner_bp.route("/listings/<int:lid>", methods=["DELETE"])
@jwt_required()
def delete_listing(lid):
    user_id = int(get_jwt_identity())
    listing = LandListing.query.filter_by(id=lid, owner_id=user_id).first_or_404()
    db.session.delete(listing)
    db.session.commit()
    return jsonify({"deleted": True})


@landowner_bp.route("/lease-requests", methods=["GET"])
@jwt_required()
def get_lease_requests():
    user_id = int(get_jwt_identity())
    listings = LandListing.query.filter_by(owner_id=user_id).all()
    listing_ids = [l.id for l in listings]
    page = request.args.get("page", 1, type=int)
    paginated = (LeaseRequest.query
                 .filter(LeaseRequest.listing_id.in_(listing_ids))
                 .order_by(LeaseRequest.created_at.desc())
                 .paginate(page=page, per_page=20, error_out=False))
    return jsonify({
        "requests": [r.to_dict() for r in paginated.items],
        "total": paginated.total,
        "page": page,
    })


@landowner_bp.route("/lease-requests/<int:rid>/respond", methods=["POST"])
@jwt_required()
def respond_lease(rid):
    user_id = int(get_jwt_identity())
    req = LeaseRequest.query.get_or_404(rid)
    listing = LandListing.query.filter_by(id=req.listing_id, owner_id=user_id).first()
    if not listing:
        return jsonify({"error": "Unauthorized"}), 403
    action = (request.get_json() or {}).get("action")
    if action not in ("accept", "reject"):
        return jsonify({"error": "action must be accept or reject"}), 400
    req.status = "accepted" if action == "accept" else "rejected"
    if action == "accept":
        listing.status = "leased"
    # Notify requester
    owner = User.query.get(user_id)
    push_notification(
        user_id=req.requester_id,
        title=f"Lease request {req.status}",
        body=f"{owner.full_name} {req.status} your request for '{listing.title}' (₹{req.offered_monthly:,.0f}/mo).",
        notif_type=f"lease_{req.status}",
        entity_id=req.id,
    )
    db.session.commit()
    return jsonify({"status": req.status})


@landowner_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    listings = LandListing.query.filter_by(owner_id=user_id).all()
    listing_ids = [l.id for l in listings]
    pending = LeaseRequest.query.filter(
        LeaseRequest.listing_id.in_(listing_ids),
        LeaseRequest.status == "pending"
    ).count()
    return jsonify({
        "total_listings": len(listings),
        "active_listings": sum(1 for l in listings if l.status == "active"),
        "leased_listings": sum(1 for l in listings if l.status == "leased"),
        "pending_requests": pending,
        "monthly_revenue": sum(l.monthly_lease for l in listings if l.status == "leased" and l.monthly_lease),
    })
