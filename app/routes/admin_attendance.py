from flask import Blueprint, request, jsonify, current_app
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

    try:
        admin_id = int(get_jwt_identity())
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    # Admin exists?
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({"attendance": [], "meta": {}}), 200

    # Date Filter (YYYY-MM-DD)
    date_str = request.args.get("date")
    
    start_time = None
    end_time = None

    if date_str:
        try:
            # Use explicit string range for maximum compatibility
            start_time = f"{date_str} 00:00:00"
            end_time = f"{date_str} 23:59:59"
        except Exception as e:
            current_app.logger.warning(f"Invalid date format: {date_str} - {e}")
            return jsonify({"error": "Invalid date format"}), 400
    
    # Month Filter (YYYY-MM)
    month_param = request.args.get("month")
    if month_param:
        try:
            part_year, part_month = map(int, month_param.split('-'))
            start_time = datetime(part_year, part_month, 1)
            if part_month == 12:
                end_time = datetime(part_year + 1, 1, 1)
            else:
                end_time = datetime(part_year, part_month + 1, 1)
        except ValueError:
            return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

    # Pagination
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
    except ValueError:
        page = 1
        per_page = 25

    try:
        # Query all users of this admin
        # Explicit join to avoid ambiguity
        base_query = db.session.query(Attendance).join(User, Attendance.user_id == User.id).filter(User.admin_id == admin_id)

        # User Filter (ADDED)
        user_id = request.args.get("user_id")
        if user_id and user_id != "all":
            try:
                base_query = base_query.filter(Attendance.user_id == int(user_id))
            except ValueError:
                pass

        if start_time and end_time:
            # Note: For strict day filter we used inclusive end_time (23:59:59).
            # For month filter we calculated start of NEXT month, so use < for end_time.
            # But wait, date filter set end_time to 23:59:59.
            # Let's standardize.
            
            if month_param:
                 base_query = base_query.filter(Attendance.check_in >= start_time, Attendance.check_in < end_time)
            else:
                 # Standard date filter
                 base_query = base_query.filter(Attendance.check_in >= start_time, Attendance.check_in <= end_time)


        paginated = base_query.order_by(Attendance.check_in.desc()).paginate(page=page, per_page=per_page, error_out=False)

        results = []
        for a in paginated.items:
            results.append({
                "id": a.id,
                "user_id": a.user_id,
                "user_name": a.user.name if a.user else "Unknown",
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

    except Exception as e:
        current_app.logger.exception("Admin attendance query failed")
        return jsonify({"error": "Internal server error"}), 500