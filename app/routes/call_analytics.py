# app/routes/call_analytics.py

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db, User, CallHistory
from app.models import db


bp = Blueprint("call_analytics", __name__, url_prefix="/api/call-analytics")


# ===============================================================
# 1️⃣  SYNC ANALYTICS  (POST)
#     Saves last_sync + returns analytics summary
# ===============================================================
@bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_analytics():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if not user.is_active:
            return jsonify({"error": "User inactive"}), 403

        # ---- Total Calls ----
        total_calls = CallHistory.query.filter_by(user_id=user_id).count()

        # ---- Call Type Summary ----
        call_types = (
            db.session.query(
                CallHistory.call_type,
                func.count(CallHistory.id)
            )
            .filter(CallHistory.user_id == user_id)
            .group_by(CallHistory.call_type)
            .all()
        )

        call_type_summary = {ctype: count for ctype, count in call_types}

        # ---- Total Call Duration ----
        total_duration = (
            db.session.query(func.coalesce(func.sum(CallHistory.duration), 0))
            .filter(CallHistory.user_id == user_id)
            .scalar()
            or 0
        )

        # ---- Update Last Sync ----
        user.last_sync = datetime.utcnow()
        db.session.commit()

        # ---- Final Response ----
        return jsonify({
            "message": "Analytics synced successfully",
            "user_id": user_id,
            "total_calls": total_calls,
            "call_types": call_type_summary,
            "total_duration_seconds": total_duration,
            "last_sync": user.last_sync.isoformat()
        }), 200

    except Exception as e:
        current_app.logger.exception("SYNC ERROR")
        return jsonify({"error": str(e)}), 400


# ===============================================================
# 2️⃣  GET ANALYTICS (GET)
#     Returns full analytics with last 10 calls
# ===============================================================
@bp.route("", methods=["GET"])
@jwt_required()
def get_analytics():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if not user.is_active:
            return jsonify({"error": "User inactive"}), 403

        # ---- Total Calls ----
        total_calls = CallHistory.query.filter_by(user_id=user_id).count()

        # ---- Each Call Type ----
        incoming = CallHistory.query.filter_by(user_id=user_id, call_type="incoming").count()
        outgoing = CallHistory.query.filter_by(user_id=user_id, call_type="outgoing").count()
        missed = CallHistory.query.filter_by(user_id=user_id, call_type="missed").count()
        rejected = CallHistory.query.filter_by(user_id=user_id, call_type="rejected").count()

        # ---- Total Duration ----
        total_duration = (
            db.session.query(func.coalesce(func.sum(CallHistory.duration), 0))
            .filter(CallHistory.user_id == user_id)
            .scalar()
            or 0
        )

        # ---- Recent 10 Calls (last 7 days) ----
        week_ago = datetime.utcnow() - timedelta(days=7)

        recent_calls = (
            CallHistory.query.filter(
                CallHistory.user_id == user_id,
                CallHistory.timestamp >= week_ago
            )
            .order_by(CallHistory.timestamp.desc())
            .limit(10)
            .all()
        )

        recent_calls_data = [
            {
                "id": c.id,
                "phone_number": c.phone_number,
                "call_type": c.call_type,
                "duration": c.duration,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None
            }
            for c in recent_calls
        ]

        # ---- Final Response ----
        return jsonify({
            "user_id": user_id,
            "total_calls": total_calls,
            "incoming": incoming,
            "outgoing": outgoing,
            "missed": missed,
            "rejected": rejected,
            "total_duration_seconds": total_duration,
            "recent_calls": recent_calls_data,
            "last_sync": user.last_sync.isoformat() if user.last_sync else None
        }), 200

    except Exception as e:
        current_app.logger.exception("GET ANALYTICS ERROR")
        return jsonify({"error": str(e)}), 400
