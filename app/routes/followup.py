from flask import Blueprint, request, jsonify, current_app
from ..models import db, Followup, User
from datetime import datetime, timedelta

bp = Blueprint("followup", __name__, url_prefix="/api")

@bp.route("/followup/create", methods=["POST"])
def create_followup():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["reminder_id", "user_id", "phone", "date_time"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if user exists
        user = User.query.get(data["user_id"])
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Parse date_time
        try:
            # Handle potential ISO format differences
            dt_str = data["date_time"].replace('Z', '+00:00')
            date_time = datetime.fromisoformat(dt_str)
        except ValueError:
            return jsonify({"error": "Invalid date_time format"}), 400

        # Parse created_at if provided, else now
        created_at = datetime.utcnow()
        if "created_at" in data:
            try:
                cat_str = data["created_at"].replace('Z', '+00:00')
                created_at = datetime.fromisoformat(cat_str)
            except ValueError:
                pass # Fallback to now

        followup = Followup(
            id=data["reminder_id"],
            user_id=data["user_id"],
            contact_name=data.get("contact_name"),
            phone=data["phone"],
            message=data.get("message"),
            date_time=date_time,
            created_at=created_at,
            status="pending"
        )

        db.session.add(followup)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Reminder saved",
            "reminder_id": followup.id
        }), 201

    except Exception as e:
        current_app.logger.exception("Create followup failed")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/admin/followups", methods=["GET"])
@bp.route("/admin/followups", methods=["GET"])
def get_admin_followups():
    try:
        user_id = request.args.get("user_id")
        date_filter = request.args.get("filter") # today, tomorrow, yesterday, all
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = Followup.query

        # Apply User Filter
        if user_id and user_id.lower() != "all":
            query = query.filter_by(user_id=user_id)

        # Apply Date Filter
        if date_filter and date_filter.lower() != "all":
            now = datetime.utcnow() # Use UTC for consistency if stored as UTC
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if date_filter == "today":
                query = query.filter(Followup.date_time >= today_start, 
                                     Followup.date_time < today_start + timedelta(days=1))
            elif date_filter == "tomorrow":
                tomorrow_start = today_start + timedelta(days=1)
                query = query.filter(Followup.date_time >= tomorrow_start, 
                                     Followup.date_time < tomorrow_start + timedelta(days=1))
            elif date_filter == "yesterday":
                yesterday_start = today_start - timedelta(days=1)
                query = query.filter(Followup.date_time >= yesterday_start, 
                                     Followup.date_time < today_start)

        # Sort
        query = query.order_by(Followup.date_time.asc())
        
        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        followups = pagination.items
        
        result = [f.to_dict() for f in followups]
        
        return jsonify({
            "followups": result,
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page
        }), 200
        
    except Exception as e:
        current_app.logger.exception("Fetch followups failed")
        return jsonify({"error": str(e)}), 500

@bp.route("/admin/followup/<string:id>", methods=["DELETE"])
def delete_followup(id):
    try:
        followup = Followup.query.get(id)
        if not followup:
            return jsonify({"error": "Reminder not found"}), 404
            
        db.session.delete(followup)
        db.session.commit()
        
        return jsonify({"message": "Reminder deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Delete followup failed")
        return jsonify({"error": str(e)}), 500
