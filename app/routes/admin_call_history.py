# app/routes/admin_all_call_history.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from app.models import db, User, CallHistory

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
        custom_date = request.args.get("date")  # YYYY-MM-DD format
        
        now = datetime.utcnow()
        start_time = None

        if filter_type == "today":
            start_time = datetime(now.year, now.month, now.day)
        elif filter_type == "week":
            start_time = now - timedelta(days=7)
        elif filter_type == "month":
            start_time = now - timedelta(days=30)
        elif custom_date:
            try:
                start_time = datetime.strptime(custom_date, "%Y-%m-%d")
            except:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # ============================
        # 2️⃣ PHONE SEARCH FILTER
        # ============================
        search = request.args.get("search")
        
        # ============================
        # 3️⃣ CALL TYPE FILTER
        # ============================
        call_type = request.args.get("call_type")  # incoming/outgoing/missed

        # ============================
        # BASE QUERY (JOIN + ADMIN FILTER)
        # ============================
        query = (
            db.session.query(CallHistory, User)
            .join(User, CallHistory.user_id == User.id)
            .filter(User.admin_id == admin_id)
        )

        # Apply date filter
        if start_time:
            query = query.filter(CallHistory.timestamp >= start_time)

        # Apply phone number search
        if search:
            query = query.filter(CallHistory.phone_number.like(f"%{search}%"))

        # Apply call type filter
        if call_type:
            query = query.filter(CallHistory.call_type == call_type)

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
# app/routes/admin_all_call_history.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from app.models import db, User, CallHistory

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
        custom_date = request.args.get("date")  # YYYY-MM-DD format
        
        now = datetime.utcnow()
        start_time = None

        if filter_type == "today":
            start_time = datetime(now.year, now.month, now.day)
        elif filter_type == "week":
            start_time = now - timedelta(days=7)
        elif filter_type == "month":
            start_time = now - timedelta(days=30)
        elif custom_date:
            try:
                start_time = datetime.strptime(custom_date, "%Y-%m-%d")
            except:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # ============================
        # 2️⃣ PHONE SEARCH FILTER
        # ============================
        search = request.args.get("search")
        
        # ============================
        # 3️⃣ CALL TYPE FILTER
        # ============================
        call_type = request.args.get("call_type")  # incoming/outgoing/missed

        # ============================
        # BASE QUERY (JOIN + ADMIN FILTER)
        # ============================
        query = (
            db.session.query(CallHistory, User)
            .join(User, CallHistory.user_id == User.id)
            .filter(User.admin_id == admin_id)
        )

        # Apply date filter
        if start_time:
            query = query.filter(CallHistory.timestamp >= start_time)

        # Apply phone number search
        if search:
            query = query.filter(CallHistory.phone_number.like(f"%{search}%"))

        # Apply call type filter
        if call_type:
            query = query.filter(CallHistory.call_type == call_type)

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