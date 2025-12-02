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
    try:
        total_calls = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids)).scalar() or 0

        incoming = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.call_type == "incoming").scalar() or 0

        outgoing = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.call_type == "outgoing").scalar() or 0

        missed = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.call_type == "missed").scalar() or 0

        rejected = db.session.query(func.count(CallHistory.id))\
            .filter(CallHistory.user_id.in_(user_ids), CallHistory.call_type == "rejected").scalar() or 0

    except Exception:
        total_calls = incoming = outgoing = missed = rejected = 0

    # ---------- Daily trend (last 7 days) ----------
    week_ago = datetime.utcnow() - timedelta(days=7)

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

    daily_trend = []
    for i in range(7, 0, -1):
        d = (datetime.utcnow() - timedelta(days=i - 1)).date()
        d_str = str(d)
        daily_trend.append({
            "date": d_str,
            "count": trend_map.get(d_str, 0)
        })

    # ---------- User summary ----------
    summary_rows = (
        db.session.query(
            User.id.label("user_id"),
            User.name.label("user_name"),

            func.coalesce(func.sum(
                case((CallHistory.call_type == "incoming", 1), else_=0)
            ), 0).label("incoming"),

            func.coalesce(func.sum(
                case((CallHistory.call_type == "outgoing", 1), else_=0)
            ), 0).label("outgoing"),

            func.coalesce(func.sum(
                case((CallHistory.call_type == "missed", 1), else_=0)
            ), 0).label("missed"),

            func.coalesce(func.sum(
                case((CallHistory.call_type == "rejected", 1), else_=0)
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
        "incoming": int(incoming),
        "outgoing": int(outgoing),
        "missed": int(missed),
        "rejected": int(rejected),
        "daily_trend": daily_trend,
        "user_summary": user_summary
    }), 200
