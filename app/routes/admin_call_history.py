# app/routes/admin_call_history.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from app.models import db, User, CallHistory
from sqlalchemy import or_, func

bp = Blueprint("admin_all_call_history", __name__, url_prefix="/api/admin")


def admin_required(fn):
    def wrapper(*args, **kwargs):
        if get_jwt().get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


@bp.route("/all-call-history", methods=["GET"])
@jwt_required()
@admin_required
def all_call_history():
    try:
        admin_id = int(get_jwt_identity())

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))

        # ============================
        # 1️⃣ DATE FILTER
        # ============================
        filter_type = request.args.get("filter")  # today / week / month
        custom_date = request.args.get("date", "").strip()  # YYYY-MM-DD format
        
        now = datetime.utcnow()
        start_time = None

        if filter_type == "today":
            start_time = datetime(now.year, now.month, now.day)
        elif filter_type == "week":
            start_time = now - timedelta(days=7)
        elif filter_type == "month":
            start_time = now - timedelta(days=30)

        # ============================
        # 2️⃣ PHONE SEARCH FILTER
        # ============================
        search = request.args.get("search")
        
        # ============================
        # 3️⃣ CALL TYPE FILTER
        # ============================
        call_type = request.args.get("call_type")  # incoming/outgoing/missed

        # ============================
        # 4️⃣ USER FILTER
        # ============================
        user_id = request.args.get("user_id")
        if user_id and user_id != "all":
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None

        # ============================
        # BASE QUERY (JOIN + ADMIN FILTER)
        # ============================
        query = (
            db.session.query(CallHistory, User)
            .join(User, CallHistory.user_id == User.id)
            .filter(User.admin_id == admin_id)
        )

        # Apply date filter
        if custom_date:
            try:
                # Use func.date to compare just the date part, avoiding time/range issues
                # This assumes the DB dialect supports date() or similar (Postgres/MySQL/SQLite do)
                query = query.filter(func.date(CallHistory.timestamp) == custom_date)
            except Exception as e:
                return jsonify({"error": "Invalid date format or query error"}), 400
        elif start_time:
            query = query.filter(CallHistory.timestamp >= start_time)

        # Apply phone number search
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    CallHistory.phone_number.ilike(search_term),
                    CallHistory.formatted_number.ilike(search_term),
                    func.lower(CallHistory.contact_name).like(search_term)
                )
            )

        # Apply call type filter
        if call_type:
            query = query.filter(func.lower(CallHistory.call_type) == call_type.lower())

        # Apply user filter
        if user_id:
            query = query.filter(CallHistory.user_id == user_id)

        # Sorting
        query = query.order_by(CallHistory.timestamp.desc())

        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        data = []
        for rec, user in paginated.items:
            data.append({
                "id": rec.id,
                "user_id": rec.user_id,
                "user_name": user.name,
                "phone_number": rec.phone_number,
                "formatted_number": rec.formatted_number,
                "contact_name": rec.contact_name,
                "call_type": rec.call_type,
                "duration": rec.duration,
                "timestamp": rec.timestamp.isoformat() if rec.timestamp else None,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            })

        return jsonify({
            "call_history": data,
            "meta": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal error", "detail": str(e)}), 400