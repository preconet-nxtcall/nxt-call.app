# app/routes/admin_performance.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_, or_, case
from datetime import datetime, timedelta

from app.models import db, CallHistory, User, Admin

bp = Blueprint("admin_performance", __name__, url_prefix="/api/admin")


# ---------------------------
# Helper: Date Range Filter
# ---------------------------
def get_date_range(filter_type):
    now = datetime.utcnow()

    if filter_type == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)

    elif filter_type == "week":
        start = now - timedelta(days=7)
        end = now

    elif filter_type == "month":
        start = now - timedelta(days=30)
        end = now

    else:
        start = datetime(2000, 1, 1)
        end = now

    return start, end


# ---------------------------
# GET /api/admin/performance
# ---------------------------
@bp.route("/performance", methods=["GET"])
@jwt_required()
def performance():
    try:
        admin_id = int(get_jwt_identity())
        admin = Admin.query.get(admin_id)

        if not admin:
            return jsonify({"error": "Unauthorized"}), 401

        # Load filter
```python
# app/routes/admin_performance.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_, or_, case
from datetime import datetime, timedelta

from app.models import db, CallHistory, User, Admin

bp = Blueprint("admin_performance", __name__, url_prefix="/api/admin")


# ---------------------------
# Helper: Date Range Filter
# ---------------------------
def get_date_range(filter_type):
    now = datetime.utcnow()

    if filter_type == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)

    elif filter_type == "week":
        start = now - timedelta(days=7)
        end = now

    elif filter_type == "month":
        start = now - timedelta(days=30)
        end = now

    else:
        start = datetime(2000, 1, 1)
        end = now

    return start, end


# ---------------------------
# GET /api/admin/performance
# ---------------------------
@bp.route("/performance", methods=["GET"])
@jwt_required()
def performance():
    try:
        admin_id = int(get_jwt_identity())
        admin = Admin.query.get(admin_id)

        if not admin:
            return jsonify({"error": "Unauthorized"}), 401

        # Load filter
        filter_type = request.args.get("filter", "today")
        start_dt, end_dt = get_date_range(filter_type)
        
        # User Filter
        user_id_param = request.args.get("user_id", "all")

        # CASE expressions (Standardized List Syntax)
        incoming_case = case([(func.lower(CallHistory.call_type) == "incoming", 1)], else_=0)
        outgoing_case = case([(func.lower(CallHistory.call_type) == "outgoing", 1)], else_=0)
        missed_case = case([(func.lower(CallHistory.call_type) == "missed", 1)], else_=0)
        rejected_case = case([(func.lower(CallHistory.call_type) == "rejected", 1)], else_=0)

        # Base query with Date Filter in OUTER JOIN
        # This ensures we keep users even if they have no calls in the date range
        query = db.session.query(
            User.id,
            User.name,
            func.count(CallHistory.id).label("total_calls"),
            func.sum(CallHistory.duration).label("total_duration"),
            func.sum(incoming_case).label("incoming"),
            func.sum(outgoing_case).label("outgoing"),
            func.sum(missed_case).label("missed"),
            func.sum(rejected_case).label("rejected"),
        ).outerjoin(
            CallHistory, 
            and_(
                CallHistory.user_id == User.id,
                CallHistory.timestamp >= start_dt,
                CallHistory.timestamp < end_dt
            )
        )

        # Apply Admin Filter
        filters = [User.admin_id == admin_id]

        # Apply User Filter
        if user_id_param and user_id_param != "all":
            try:
                uid = int(user_id_param)
                filters.append(User.id == uid)
            except ValueError:
                pass # Ignore invalid user_id

        # Execute Query
        user_data = (
            query.filter(*filters)
            .group_by(User.id)
            .all()
        )

        # Format response
        users_list = []
        for u in user_data:
            users_list.append({
                "user_id": u.id,
                "user_name": u.name,
                "total_calls": int(u.total_calls or 0),
                "total_duration_sec": int(u.total_duration or 0),
                "incoming": int(u.incoming or 0),
                "outgoing": int(u.outgoing or 0),
                "missed": int(u.missed or 0),
                "rejected": int(u.rejected or 0),
            })

        # Calculate Score (Simple: Incoming + Outgoing)
        # You can make this more complex (e.g. weighted)
        for u in users_list:
            u["score"] = u["incoming"] + u["outgoing"]

        # Sort
        sort_order = request.args.get("sort", "desc")
        reverse = (sort_order == "desc")
        users_list.sort(key=lambda x: x["score"], reverse=reverse)

        # Prepare response for Chart.js and Table
        labels = [u["user_name"] for u in users_list]
        values = [u["score"] for u in users_list]
        user_ids = [u["user_id"] for u in users_list]
        
        # Detailed data arrays for table
        incoming_counts = [u["incoming"] for u in users_list]
        outgoing_counts = [u["outgoing"] for u in users_list]
        total_counts = [u["total_calls"] for u in users_list]

        return jsonify({
            "labels": labels,
            "values": values,
            "user_ids": user_ids,
            "incoming": incoming_counts,
            "outgoing": outgoing_counts,
            "total_calls": total_counts
        }), 200

    except Exception as e:
        print(f"Performance error: {e}") # Log to console
        return jsonify({"error": str(e)}), 400
```
