from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from sqlalchemy import func

from ..models import db, Admin, Attendance, User

bp = Blueprint("admin_attendance", __name__, url_prefix="/api/admin/attendance")

def admin_required():
    claims = get_jwt()
    return claims.get("role") == "admin"


@bp.route("", methods=["GET"])
@jwt_required()
def get_admin_attendance():
    """Return FULL attendance data for admin dashboard."""
    
    # Must be admin
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    admin_id = int(get_jwt_identity())

    # Admin exists?
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({"attendance": [], "meta": {}}), 200

    # Time Filter (today/week/month)
    filter_type = request.args.get("filter", "today")

    now = datetime.utcnow()
    start_time = None

    if filter_type == "today":
        start_time = datetime(now.year, now.month, now.day)
    elif filter_type == "week":
        start_time = now - timedelta(days=7)
    elif filter_type == "month":
        start_time = now - timedelta(days=30)

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))

    # Query all users of this admin
    base_query = db.session.query(Attendance).join(User).filter(User.admin_id == admin_id)

    if start_time:
        base_query = base_query.filter(Attendance.check_in >= start_time)

    paginated = base_query.order_by(Attendance.check_in.desc()).paginate(page=page, per_page=per_page, error_out=False)

    results = []
    for a in paginated.items:
        results.append({
            "id": a.id,
            "user_id": a.user_id,
            "user_name": a.user.name if a.user else None,
            "status": a.status,
            "check_in": a.check_in.isoformat() if a.check_in else None,
            "check_out": a.check_out.isoformat() if a.check_out else None,
            "address": a.address,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "image_path": a.image_path,
            "synced": a.synced,
            "external_id": a.external_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "sync_timestamp": a.sync_timestamp.isoformat() if a.sync_timestamp else None
        })

    return jsonify({
        "attendance": results,
        "meta": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev
        }
    }), 200