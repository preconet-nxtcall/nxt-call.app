from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models import User, CallHistory, Admin
from sqlalchemy import func

bp = Blueprint("admin_dashboard_data", __name__, url_prefix="/api/admin")

# 1️⃣ DASHBOARD CARDS
@bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    admin_id = int(get_jwt_identity())

    # Get all users under admin
    users = User.query.filter_by(admin_id=admin_id).all()

    total_users = len(users)
    active_users = sum(1 for u in users if u.is_active)
    users_with_sync = sum(1 for u in users if u.last_sync is not None)

    admin = Admin.query.get(admin_id)
    remaining_slots = admin.max_users - total_users if admin else 0

    return jsonify({
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "users_with_sync": users_with_sync,
            "remaining_slots": remaining_slots,
            "performance_trend": [12, 18, 10, 25, 16, 20, 30]
        }
    }), 200


# 2️⃣ RECENT SYNC LIST
@bp.route("/recent-sync", methods=["GET"])
@jwt_required()
def recent_sync():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    admin_id = int(get_jwt_identity())

    users = User.query.filter_by(admin_id=admin_id).all()

    result = []
    for u in users:
        result.append({
            "name": u.name,
            "last_sync": u.last_sync.isoformat() if u.last_sync else None,
            "is_active": u.is_active
        })

    # Sort by last sync
    result.sort(key=lambda x: x["last_sync"] or "", reverse=True)

    return jsonify({"recent_sync": result}), 200


# 3️⃣ USER LOGS (Dummy for now)
@bp.route("/user-logs", methods=["GET"])
@jwt_required()
def user_logs():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    return jsonify({
        "logs": [
            {"user_name": "System", "action": "Dashboard opened", "timestamp": str(func.now())}
        ]
    }), 200
