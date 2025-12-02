# app/routes/admin_dashboard.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db

from ..models import User, Admin, Attendance, CallHistory, ActivityLog

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
            "performance_trend": [50, 60, 70, 65, 82, 78, 90]
        }
    }), 200


# =========================================================
# 2️⃣ FIXED — RECENT SYNC LAST 10 USERS
# =========================================================
@admin_dashboard_bp.route("/recent-sync", methods=["GET"])
@jwt_required()
def recent_sync():
    if not admin_required():
        return jsonify({"error": "Admin only"}), 403

    admin_id = int(get_jwt_identity())

    users = (
        User.query
        .filter(User.admin_id == admin_id)
        .order_by(User.last_sync.desc().nullslast())
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


# =========================================================
# 3️⃣ USER ACTIVITY LOGS (latest 20)
# =========================================================
@admin_dashboard_bp.route("/user-logs", methods=["GET"])
@jwt_required()
def user_logs():
    if not admin_required():
        return jsonify({"error": "Admin only"}), 403

    admin_id = int(get_jwt_identity())

    logs = (
        db.session.query(ActivityLog, User)
        .join(User, User.id == ActivityLog.target_id)
        .filter(User.admin_id == admin_id)
        .order_by(ActivityLog.timestamp.desc())
        .limit(20)
        .all()
    )

    return jsonify({
        "logs": [
            {
                "user_name": u.name,
                "action": log.action,
                "timestamp": iso(log.timestamp)
            }
            for log, u in logs
        ]
    }), 200


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

