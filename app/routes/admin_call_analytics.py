# app/routes/admin_call_analytics.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func, case
from app.models import db, User, CallHistory
from datetime import datetime, timedelta

bp = Blueprint("admin_call_analytics", __name__, url_prefix="/api/admin/call-analytics")


def is_admin():
    return get_jwt().get("role") == "admin"


@bp.route("", methods=["GET"])
@jwt_required()
def admin_analytics_all_users():
    """
    Returns aggregated analytics for ALL users under the admin.
    """
    if not is_admin():
        return jsonify({"error": "Admin access required"}), 403

    try:
        admin_id = int(get_jwt_identity())

        # Get users under admin
        users = User.query.filter_by(admin_id=admin_id).all()
        user_ids = [u.id for u in users]

        if not user_ids:
            return jsonify({
                "total_calls": 0,
                "incoming": 0,
                "outgoing": 0,
                "missed": 0,
                "rejected": 0,
                "daily_trend": [],
                "user_summary": []
            }), 200

        # ---------- Top-level totals ----------
        # Removed inner try-except to expose errors
        total_calls = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids)).scalar() or 0

        incoming = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "incoming").scalar() or 0

        outgoing = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "outgoing").scalar() or 0

        missed = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "missed").scalar() or 0

        rejected = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "rejected").scalar() or 0

        # New Metrics
        total_answered = incoming + outgoing

        unique_numbers = db.session.query(func.count(func.distinct(CallHistory.phone_number)))\
            .filter(CallHistory.user_id.in_(user_ids)).scalar() or 0

        avg_inbound_duration = db.session.query(func.avg(CallHistory.duration))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "incoming").scalar() or 0

        avg_outbound_duration = db.session.query(func.avg(CallHistory.duration))\
            .filter(CallHistory.user_id.in_(user_ids), func.lower(CallHistory.call_type) == "outgoing").scalar() or 0
        
        total_duration = db.session.query(func.sum(CallHistory.duration))\
            .filter(CallHistory.user_id.in_(user_ids)).scalar() or 0

        # ---------- Daily trend (last 7 days) ----------
        week_ago = datetime.utcnow() - timedelta(days=7)

        # Activity Trend (Count)
        trend_rows = (
            db.session.query(
                func.date(CallHistory.timestamp).label("date"),
                func.count(CallHistory.id).label("count"),
                func.sum(CallHistory.duration).label("duration")
            )
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.timestamp >= week_ago)
            .group_by(func.date(CallHistory.timestamp))
            .order_by(func.date(CallHistory.timestamp))
            .all()
        )

        trend_map = {str(r.date): {"count": int(r.count), "duration": int(r.duration or 0)} for r in trend_rows}

        daily_trend = []
        duration_trend = []
        
        for i in range(7, 0, -1):
            d = (datetime.utcnow() - timedelta(days=i - 1)).date()
            d_str = str(d)
            data = trend_map.get(d_str, {"count": 0, "duration": 0})
            
            daily_trend.append({
                "date": d_str,
                "count": data["count"]
            })
            duration_trend.append({
                "date": d_str,
                "duration": data["duration"]
            })

        # ---------- User summary ----------
        summary_rows = (
            db.session.query(
                User.id.label("user_id"),
                User.name.label("user_name"),

                func.coalesce(func.sum(
                    case((func.lower(CallHistory.call_type) == "incoming", 1), else_=0)
                ), 0).label("incoming"),

                func.coalesce(func.sum(
                    case((func.lower(CallHistory.call_type) == "outgoing", 1), else_=0)
                ), 0).label("outgoing"),

                func.coalesce(func.sum(
                    case((func.lower(CallHistory.call_type) == "missed", 1), else_=0)
                ), 0).label("missed"),

                func.coalesce(func.sum(
                    case((func.lower(CallHistory.call_type) == "rejected", 1), else_=0)
                ), 0).label("rejected"),

                func.coalesce(func.sum(CallHistory.duration), 0).label("total_duration_seconds"),

                User.last_sync.label("last_sync")
            )
            .outerjoin(CallHistory, User.id == CallHistory.user_id)
            .filter(User.admin_id == admin_id)
            .group_by(User.id)
            .order_by(User.name)
            .all()
        )

        user_summary = []
        for r in summary_rows:
            user_summary.append({
                "user_id": int(r.user_id),
                "user_name": r.user_name,
                "incoming": int(r.incoming),
                "outgoing": int(r.outgoing),
                "missed": int(r.missed),
                "rejected": int(r.rejected),
                "total_duration_seconds": int(r.total_duration_seconds or 0),
                "last_sync": r.last_sync.isoformat() if r.last_sync else None
            })

        # ---------- Final response ----------
        return jsonify({
            "total_calls": int(total_calls),
            "total_duration": int(total_duration),
            "incoming": int(incoming),
            "outgoing": int(outgoing),
            "missed": int(missed),
            "rejected": int(rejected),
            "total_answered": int(total_answered),
            "unique_numbers": int(unique_numbers),
            "avg_inbound_duration": int(avg_inbound_duration),
            "avg_outbound_duration": int(avg_outbound_duration),
            "daily_trend": daily_trend,
            "duration_trend": duration_trend,
            "user_summary": user_summary
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def admin_analytics_single_user(user_id):
    """
    Returns analytics for a SINGLE user for a specific period (default: today).
    """
    if not is_admin():
        return jsonify({"error": "Admin access required"}), 403

    try:
        admin_id = int(get_jwt_identity())

        # Verify user belongs to admin
        user = User.query.filter_by(id=user_id, admin_id=admin_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Determine date range (default: today)
        period = request.args.get("period", "today")
        now = datetime.utcnow()
        
        if period == "today":
            start_dt = datetime(now.year, now.month, now.day)
            end_dt = start_dt + timedelta(days=1)
        elif period == "week":
            start_dt = datetime(now.year, now.month, now.day) - timedelta(days=7)
            end_dt = datetime(now.year, now.month, now.day) + timedelta(days=1)
        elif period == "month":
            start_dt = datetime(now.year, now.month, now.day) - timedelta(days=30)
            end_dt = datetime(now.year, now.month, now.day) + timedelta(days=1)
        elif period == "all":
            start_dt = datetime.min
            end_dt = datetime.max
        else:
            # Fallback to today if unknown
            start_dt = datetime(now.year, now.month, now.day)
            end_dt = start_dt + timedelta(days=1)

        # Query stats
        stats = db.session.query(
            func.count(CallHistory.id).label("total"),
            func.sum(case((func.lower(CallHistory.call_type) == "incoming", 1), else_=0)).label("incoming"),
            func.sum(case((func.lower(CallHistory.call_type) == "outgoing", 1), else_=0)).label("outgoing"),
            func.sum(case((func.lower(CallHistory.call_type) == "missed", 1), else_=0)).label("missed"),
            func.sum(case((func.lower(CallHistory.call_type) == "rejected", 1), else_=0)).label("rejected"),
            func.sum(CallHistory.duration).label("duration")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.timestamp >= start_dt,
            CallHistory.timestamp < end_dt
        ).first()

        return jsonify({
            "user_name": user.name,
            "period": period,
            "total_calls": int(stats.total or 0),
            "incoming": int(stats.incoming or 0),
            "outgoing": int(stats.outgoing or 0),
            "missed": int(stats.missed or 0),
            "rejected": int(stats.rejected or 0),
            "total_duration_seconds": int(stats.duration or 0)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
