# app/routes/admin_dashboard.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db

from app.models import User, Admin, Attendance, CallHistory, ActivityLog

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/api/admin")


# ---------------------------
# HELPERS
# ---------------------------
def admin_required():
    claims = get_jwt()
    return claims.get("role") == "admin"


def iso(dt):
    if not dt:
        return None
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


# =========================================================
# 1️⃣ DASHBOARD STATS (TOP CARDS)
# =========================================================
@admin_dashboard_bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    admin_id = int(get_jwt_identity())
    admin = Admin.query.get(admin_id)

    if not admin:
        return jsonify({"error": "Admin account not found"}), 404

    users = User.query.filter_by(admin_id=admin_id).all()
    total = len(users)
    active = sum(1 for u in users if u.is_active)
    synced = sum(1 for u in users if u.last_sync)

    # Handle None values in performance_score safely
    total_score = sum((u.performance_score or 0.0) for u in users)
    avg_perf = round(total_score / total, 2) if total else 0

    # Calculate daily call trend (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    user_ids = [u.id for u in users]
    
    daily_counts = []
    if user_ids:
        trend_rows = (
            db.session.query(
                func.date(CallHistory.timestamp).label("date"),
                func.count(CallHistory.id).label("count")
            )
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.timestamp >= week_ago)
            .group_by(func.date(CallHistory.timestamp))
            .order_by(func.date(CallHistory.timestamp))
            .all()
        )
        trend_map = {str(r.date): int(r.count) for r in trend_rows}
        
        for i in range(6, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            d_str = str(d)
            daily_counts.append(trend_map.get(d_str, 0))
    else:
        daily_counts = [0] * 7

    return jsonify({
        "stats": {
            "total_users": total,
            "active_users": active,
            "expired_users": 0,
            "user_limit": admin.user_limit,
            "remaining_slots": admin.user_limit - total,
            "users_with_sync": synced,
            "sync_rate": round((synced / total) * 100, 2) if total else 0,
            "avg_performance": avg_perf,
            "performance_trend": daily_counts,
            "admin_name": admin.name,
            "admin_email": admin.email
        }
    }), 200


# =========================================================
# 2️⃣ FIXED — RECENT SYNC LAST 10 USERS
# =========================================================
@admin_dashboard_bp.route("/recent-sync", methods=["GET"])
@jwt_required()
def recent_sync():
    try:
        if not admin_required():
            return jsonify({"error": "Admin only"}), 403

        admin_id = int(get_jwt_identity())

        # Removed nullslast() to be safe across DB versions
        users = (
            User.query
            .filter(User.admin_id == admin_id)
            .order_by(User.last_sync.desc())
            .limit(10)
            .all()
        )

        return jsonify({
            "recent_sync": [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email or "-",
                    "phone": u.phone or "-",
                    "is_active": u.is_active,
                    "last_sync": iso(u.last_sync)
                }
                for u in users
            ]
        }), 200
    except Exception as e:
        print(f"Error in recent_sync: {e}")
        return jsonify({"error": str(e)}), 400


# =========================================================
# 3️⃣ USER ACTIVITY LOGS (latest 20)
# =========================================================
@admin_dashboard_bp.route("/user-logs", methods=["GET"])
@jwt_required()
def user_logs():
    try:
        if not admin_required():
            return jsonify({"error": "Admin only"}), 403

        admin_id = int(get_jwt_identity())

        # Get all users for this admin
        users = User.query.filter_by(admin_id=admin_id).all()
        
        logs = []
        for user in users:
            # Get latest attendance
            last_attendance = (
                Attendance.query.filter_by(user_id=user.id)
                .order_by(Attendance.check_in.desc())
                .first()
            )
            
            check_in_time = iso(last_attendance.check_in) if last_attendance else "Never"
            status = "Active" if user.is_active else "Inactive"
            
            logs.append({
                "user_name": user.name,
                "action": f"Status: {status}",
                "timestamp": check_in_time,
                "is_active": user.is_active
            })

        # Sort by latest check-in (optional, but good for 'recent' activity)
        # We can sort by timestamp, handling "Never"
        def sort_key(x):
            if x["timestamp"] == "Never":
                return ""
            return x["timestamp"]
            
        logs.sort(key=sort_key, reverse=True)

        return jsonify({
            "logs": logs
        }), 200
    except Exception as e:
        print(f"Error in user_logs: {e}")
        return jsonify({"error": str(e)}), 400


# =========================================================
# 4️⃣ ADMIN — ALL ATTENDANCE
# =========================================================
@admin_dashboard_bp.route("/attendance", methods=["GET"])
@jwt_required()
def admin_attendance():
    if not admin_required():
        return jsonify({"error": "Admin only"}), 403

    admin_id = int(get_jwt_identity())

    records = (
        db.session.query(Attendance, User)
        .join(User, Attendance.user_id == User.id)
        .filter(User.admin_id == admin_id)
        .order_by(Attendance.created_at.desc())
        .all()
    )

    return jsonify({
        "attendance": [
            {
                "id": a.id,
                "user_name": u.name,
                "check_in": iso(a.check_in),
                "check_out": iso(a.check_out),
                "address": a.address,
                "latitude": a.latitude,
                "longitude": a.longitude,
                "status": a.status,
            }
            for a, u in records
        ]
    }), 200


# =========================================================
# 5️⃣ ADMIN — SIMPLE CALL HISTORY (LATEST 200)
# =========================================================
@admin_dashboard_bp.route("/call-history", methods=["GET"])
@jwt_required()
def admin_call_history():
    if not admin_required():
        return jsonify({"error": "Admin only"}), 403

    admin_id = int(get_jwt_identity())

    users = User.query.filter_by(admin_id=admin_id).all()
    user_ids = [u.id for u in users]

    calls = (
        db.session.query(CallHistory, User)
        .join(User, User.id == CallHistory.user_id)
        .filter(CallHistory.user_id.in_(user_ids))
        .order_by(CallHistory.timestamp.desc())
        .limit(200)
        .all()
    )

    return jsonify({
        "call_history": [
            {
                "id": c.id,
                "user_id": u.id,
                "user_name": u.name,
                "phone_number": c.phone_number,
                "call_type": c.call_type,
                "duration": c.duration,
                "timestamp": iso(c.timestamp),
                "created_at": iso(c.created_at),
            }
            for c, u in calls
        ]
    }), 200


# =========================================================
# 6️⃣ ADMIN — CALL ANALYTICS (Frontend uses new API)
# =========================================================
# NOTE:
# This file now keeps only the LATEST-CALLS version
# The real analytics is handled in:
#   app/routes/admin_call_analytics.py
# which you already fixed and connected JS to.

