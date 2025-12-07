from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from ..models import db, Followup, User, Admin, ActivityLog, UserRole
from sqlalchemy import or_, and_

bp = Blueprint("followup", __name__, url_prefix="/api/followup")


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def admin_required():
    """Check if current user is admin"""
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    return claims.get("role") == "admin"


def get_admin_or_401():
    """Get current admin or return 401"""
    admin_id = get_jwt_identity()
    admin = Admin.query.get(admin_id)
    if not admin:
        return None, (jsonify({"error": "Admin not found"}), 401)
    if not admin.is_active:
        return None, (jsonify({"error": "Account deactivated"}), 403)
    if admin.is_expired():
        return None, (jsonify({"error": "Account expired"}), 403)
    return admin, None


# =========================================================
# CREATE FOLLOW-UP
# =========================================================
@bp.route("/create", methods=["POST"])
@jwt_required()
def create_followup():
    """Create a new follow-up reminder"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        data = request.get_json() or {}
        
        # Required fields
        user_id = data.get("user_id")
        phone = data.get("phone")
        date_time_str = data.get("date_time")
        
        if not all([user_id, phone, date_time_str]):
            return jsonify({"error": "user_id, phone, and date_time are required"}), 400
        
        # Verify user belongs to this admin
        user = User.query.filter_by(id=user_id, admin_id=admin.id).first()
        if not user:
            return jsonify({"error": "User not found or unauthorized"}), 404
        
        # Parse date_time (ISO format: 2025-12-07T14:30:00)
        try:
            date_time = datetime.fromisoformat(date_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Invalid date_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}), 400
        
        # Create followup
        followup = Followup(
            reminder_id=data.get("reminder_id"),
            user_id=user_id,
            admin_id=admin.id,
            contact_name=data.get("contact_name"),
            phone=phone,
            message=data.get("message"),
            date_time=date_time,
            status="pending"
        )
        
        db.session.add(followup)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            actor_role=UserRole.ADMIN,
            actor_id=admin.id,
            action=f"Created follow-up for {user.name}",
            target_type="followup",
            target_id=followup.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            "message": "Follow-up created successfully",
            "followup_id": followup.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Create followup failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# =========================================================
# LIST FOLLOW-UPS
# =========================================================
@bp.route("/list", methods=["GET"])
@jwt_required()
def list_followups():
    """Get all follow-ups for the current admin with optional filters"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        # Get query parameters
        status = request.args.get("status")  # pending, completed, cancelled
        user_id = request.args.get("user_id")
        date_from = request.args.get("date_from")  # YYYY-MM-DD
        date_to = request.args.get("date_to")  # YYYY-MM-DD
        search = request.args.get("search")  # Search in contact_name or phone
        
        # Base query - only this admin's followups
        query = Followup.query.filter_by(admin_id=admin.id)
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Followup.date_time >= date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                # Add one day to include the entire end date
                from datetime import timedelta
                date_to_dt = date_to_dt + timedelta(days=1)
                query = query.filter(Followup.date_time < date_to_dt)
            except ValueError:
                pass
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Followup.contact_name.ilike(search_pattern),
                    Followup.phone.ilike(search_pattern)
                )
            )
        
        
        # Pagination
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
        total = query.count()
        
        # Apply pagination and order
        followups = query.order_by(Followup.date_time.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Format response
        result = []
        for f in followups:
            user = User.query.get(f.user_id)
            result.append({
                "id": f.id,
                "reminder_id": f.reminder_id,
                "user_id": f.user_id,
                "user_name": user.name if user else "Unknown",
                "contact_name": f.contact_name,
                "phone": f.phone,
                "message": f.message,
                "date_time": f.date_time.isoformat(),
                "status": f.status,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat() if f.updated_at else None
            })
        
        
        return jsonify({
            "followups": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        current_app.logger.exception("List followups failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# =========================================================
# GET SINGLE FOLLOW-UP
# =========================================================
@bp.route("/<int:followup_id>", methods=["GET"])
@jwt_required()
def get_followup(followup_id):
    """Get a single follow-up by ID"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        followup = Followup.query.filter_by(id=followup_id, admin_id=admin.id).first()
        if not followup:
            return jsonify({"error": "Follow-up not found"}), 404
        
        user = User.query.get(followup.user_id)
        
        return jsonify({
            "followup": {
                "id": followup.id,
                "reminder_id": followup.reminder_id,
                "user_id": followup.user_id,
                "user_name": user.name if user else "Unknown",
                "contact_name": followup.contact_name,
                "phone": followup.phone,
                "message": followup.message,
                "date_time": followup.date_time.isoformat(),
                "status": followup.status,
                "created_at": followup.created_at.isoformat(),
                "updated_at": followup.updated_at.isoformat() if followup.updated_at else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.exception("Get followup failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# =========================================================
# UPDATE FOLLOW-UP
# =========================================================
@bp.route("/<int:followup_id>", methods=["PUT"])
@jwt_required()
def update_followup(followup_id):
    """Update a follow-up"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        followup = Followup.query.filter_by(id=followup_id, admin_id=admin.id).first()
        if not followup:
            return jsonify({"error": "Follow-up not found"}), 404
        
        data = request.get_json() or {}
        
        # Update fields if provided
        if "contact_name" in data:
            followup.contact_name = data["contact_name"]
        
        if "phone" in data:
            followup.phone = data["phone"]
        
        if "message" in data:
            followup.message = data["message"]
        
        if "date_time" in data:
            try:
                followup.date_time = datetime.fromisoformat(data["date_time"].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid date_time format"}), 400
        
        if "status" in data:
            if data["status"] not in ["pending", "completed", "cancelled"]:
                return jsonify({"error": "Invalid status. Must be: pending, completed, or cancelled"}), 400
            followup.status = data["status"]
        
        followup.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log activity
        user = User.query.get(followup.user_id)
        log = ActivityLog(
            actor_role=UserRole.ADMIN,
            actor_id=admin.id,
            action=f"Updated follow-up for {user.name if user else 'Unknown'}",
            target_type="followup",
            target_id=followup.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"message": "Follow-up updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Update followup failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# =========================================================
# UPDATE STATUS
# =========================================================
@bp.route("/<int:followup_id>/status", methods=["PUT"])
@jwt_required()
def update_status(followup_id):
    """Update follow-up status"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        followup = Followup.query.filter_by(id=followup_id, admin_id=admin.id).first()
        if not followup:
            return jsonify({"error": "Follow-up not found"}), 404
        
        data = request.get_json() or {}
        status = data.get("status")
        
        if not status:
            return jsonify({"error": "status is required"}), 400
        
        if status not in ["pending", "completed", "cancelled"]:
            return jsonify({"error": "Invalid status. Must be: pending, completed, or cancelled"}), 400
        
        followup.status = status
        followup.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "message": f"Status updated to {status}",
            "status": status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Update status failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# =========================================================
# DELETE FOLLOW-UP
# =========================================================
@bp.route("/<int:followup_id>", methods=["DELETE"])
@jwt_required()
def delete_followup(followup_id):
    """Delete a follow-up"""
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        followup = Followup.query.filter_by(id=followup_id, admin_id=admin.id).first()
        if not followup:
            return jsonify({"error": "Follow-up not found"}), 404
        
        user = User.query.get(followup.user_id)
        user_name = user.name if user else "Unknown"
        
        db.session.delete(followup)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            actor_role=UserRole.ADMIN,
            actor_id=admin.id,
            action=f"Deleted follow-up for {user_name}",
            target_type="followup",
            target_id=followup_id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"message": "Follow-up deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Delete followup failed")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500
