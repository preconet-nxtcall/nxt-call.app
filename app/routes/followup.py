from flask import Blueprint, request, jsonify, current_app
from ..models import db, Followup, User
from datetime import datetime

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
def get_admin_followups():
    try:
        # Fetch all followups, sorted by date_time ASC
        followups = Followup.query.order_by(Followup.date_time.asc()).all()
        
        result = [f.to_dict() for f in followups]
        
        return jsonify(result), 200 # Direct list as requested, or maybe object wrapper? 
        # Prompt says: "Return JSON list with: ..." usually implies [ { ... }, { ... } ]
        # But standard is often { "followups": [ ... ] }
        # Let's stick to the prompt implication "Return JSON list" -> list directly? 
        # Safer to return list if explicitly asked "JSON list", but usually APIs return object. 
        # I will return a list to match "Return JSON list" strictly, OR 
        # actually, for consistency with other endpoints (like users list), usually it's { users: [] }.
        # Re-reading: "Return JSON list with: ..."
        # I'll return a list.
        
    except Exception as e:
        current_app.logger.exception("Fetch followups failed")
        return jsonify({"error": str(e)}), 500
