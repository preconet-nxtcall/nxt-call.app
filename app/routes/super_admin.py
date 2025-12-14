from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from datetime import datetime
from ..models import db, SuperAdmin, Admin, User, ActivityLog, UserRole
import re

bp = Blueprint("super_admin", __name__, url_prefix="/api/superadmin")


# =========================================================
# HELPERS
# =========================================================
def _validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email or "") is not None


def _safe_enum_value(role):
    """Convert Enum to plain string"""
    try:
        return role.value
    except:
        return str(role)


# =========================================================
# SUPER ADMIN LOGIN
# =========================================================
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    super_admin = SuperAdmin.query.filter_by(email=email).first()
    if not super_admin or not super_admin.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(super_admin.id),
        additional_claims={"role": "super_admin"}
    )

    return jsonify({
        "access_token": token,
        "user": {
            "id": super_admin.id,
            "name": super_admin.name,
            "email": super_admin.email,
            "role": "super_admin",
        }
    }), 200


# =========================================================
# CREATE ADMIN
# =========================================================
@bp.route("/create-admin", methods=["POST"])
@jwt_required()
def create_admin():
    super_admin_id = get_jwt_identity()

    if not SuperAdmin.query.get(super_admin_id):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    user_limit = int(data.get("user_limit", 10))
    expiry_date_raw = data.get("expiry_date")

    # Validate required fields
    if not all([name, email, password, expiry_date_raw]):
        return jsonify({"error": "All fields required"}), 400

    # Validate email format
    if not _validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    # Check duplicate email
    if Admin.query.filter_by(email=email).first():
        return jsonify({"error": "Admin email already exists"}), 400

    # Convert expiry date (YYYY-MM-DD)
    try:
        expiry_date = datetime.strptime(expiry_date_raw, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "expiry_date must be YYYY-MM-DD"}), 400

    # Create new admin
    new_admin = Admin(
        name=name,
        email=email,
        user_limit=user_limit,
        expiry_date=expiry_date,
        created_by=super_admin_id,
    )
    new_admin.set_password(password)

    db.session.add(new_admin)
    db.session.commit()

    # Log the activity
    log = ActivityLog(
        actor_role=UserRole.SUPER_ADMIN,
        actor_id=super_admin_id,
        action=f"Created Admin: {name}",
        target_type="admin",
        target_id=new_admin.id
    )
    db.session.add(log)
    db.session.commit()

    # Automatic Notification
    try:
        from app.services.notification_service import NotificationService
        import logging
        
        logging.info(f"Attempting to send welcome email to {email}")
        result = NotificationService.send_welcome_notification(
            name=name,
            username=email,
            password=password,
            expiry_date=expiry_date,
            phone=None,
            email=email
        )
        if result:
            logging.info(f"Welcome email sent successfully to {email}")
        else:
            logging.warning(f"Welcome email failed to send to {email} - check ZEPTOMAIL credentials")
            
    except Exception as e:
        # Catch ALL errors so we never fail the request after DB commit
        import traceback
        traceback.print_exc()
        try:
            logging.error(f"CRITICAL: Failed to send notification to {email}: {e}", exc_info=True)
        except:
            print(f"CRITICAL: Failed to send notification to {email}: {e}")

    return jsonify({"message": "Admin created successfully"}), 201


# =========================================================
# GET ALL ADMINS (SUPER ADMIN)
# =========================================================
@bp.route("/admins", methods=["GET"])
@jwt_required()
def get_admins():
    try:
        admins = Admin.query.order_by(Admin.created_at.desc()).all()
        result = []

        for a in admins:
            user_count = User.query.filter_by(admin_id=a.id).count()

            result.append({
                "id": a.id,
                "name": a.name,
                "email": a.email,
                "user_limit": a.user_limit,
                "user_count": user_count,
                "is_active": a.is_active,
                "is_expired": a.is_expired(),
                "created_at": a.created_at.isoformat(),
                "last_login": a.last_login.isoformat() if a.last_login else None,
                "expiry_date": a.expiry_date.isoformat(),
            })

        return jsonify({"admins": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# DASHBOARD STATS
# =========================================================
@bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    try:
        super_admin_id = get_jwt_identity()
        super_admin = SuperAdmin.query.get(super_admin_id)

        stats = {
            "total_admins": Admin.query.count(),
            "active_admins": Admin.query.filter_by(is_active=True).count(),
            "expired_admins": Admin.query.filter(Admin.expiry_date < datetime.utcnow()).count(),
            "total_users": User.query.count(),
            "super_admin_name": super_admin.name if super_admin else "Super Admin",
            "super_admin_email": super_admin.email if super_admin else "superadmin@example.com",
        }

        return jsonify({"stats": stats}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# GET LATEST ACTIVITY LOGS
# =========================================================
@bp.route("/logs", methods=["GET"])
@jwt_required()
def activity_logs():
    try:
        # Verify super admin
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401
            
        # Optimize: Join with Admin table to get names directly
        # We want to show WHO did WHAT.
        # If actor_role is ADMIN, we join with Admin table.
        # If actor_role is SUPER_ADMIN, we just say "Super Admin".
        
        logs_query = (
            db.session.query(ActivityLog, Admin.name)
            .outerjoin(Admin, (ActivityLog.actor_id == Admin.id) & (ActivityLog.actor_role == UserRole.ADMIN))
            .order_by(ActivityLog.timestamp.desc())
            .limit(50)
            .all()
        )

        formatted = []
        for log, admin_name in logs_query:
            
            display_name = "Unknown"
            
            if log.actor_role == UserRole.SUPER_ADMIN:
                display_name = "Super Admin"
            elif log.actor_role == UserRole.ADMIN:
                display_name = admin_name if admin_name else f"Admin #{log.actor_id} (Deleted)"
            elif log.actor_role == UserRole.USER:
                display_name = f"User #{log.actor_id}"

            formatted.append({
                "id": log.id,
                "admin_name": display_name, # Frontend expects this key
                "action_type": log.action,  # We send the full action string
                "timestamp": log.timestamp.isoformat(),
                "role": log.actor_role.value
            })

        return jsonify({"logs": formatted}), 200

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return jsonify({"error": str(e)}), 500


# =========================================================
# DELETE ACTIVITY LOGS
# =========================================================
@bp.route("/logs", methods=["DELETE"])
@jwt_required()
def delete_activity_logs():
    try:
        # Verify super admin
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401

        # Delete all logs
        num_deleted = db.session.query(ActivityLog).delete()
        db.session.commit()

        # Create a new log for this action
        log = ActivityLog(
            actor_role=UserRole.SUPER_ADMIN,
            actor_id=super_admin_id,
            action="Deleted all activity logs",
            target_type="system",
            target_id=0
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"message": f"Deleted {num_deleted} logs"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =========================================================
# TOGGLE ADMIN STATUS (BLOCK/UNBLOCK)
# =========================================================
@bp.route("/admin/<int:admin_id>/status", methods=["PUT"])
@jwt_required()
def toggle_admin_status(admin_id):
    try:
        # Verify super admin
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401

        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        # Toggle status
        admin.is_active = not admin.is_active
        db.session.commit()

        action = "Unblocked" if admin.is_active else "Blocked"

        # Log activity
        log = ActivityLog(
            actor_role=UserRole.SUPER_ADMIN,
            actor_id=super_admin_id,
            action=f"{action} Admin: {admin.name}",
            target_type="admin",
            target_id=admin.id
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            "message": f"Admin {action.lower()} successfully",
            "is_active": admin.is_active
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# =========================================================
# UPDATE ADMIN (Limit & Expiry)
# =========================================================
@bp.route("/admin/<int:admin_id>", methods=["PUT"])
@jwt_required()
def update_admin(admin_id):
    try:
        # Verify super admin
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401

        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        data = request.get_json()

        # Update fields if present
        if "user_limit" in data:
            admin.user_limit = int(data["user_limit"])

        if "expiry_date" in data:
            try:
                from datetime import datetime
                admin.expiry_date = datetime.strptime(data["expiry_date"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format (YYYY-MM-DD required)"}), 400

        db.session.commit()

        # Log activity
        log = ActivityLog(
            actor_role=UserRole.SUPER_ADMIN,
            actor_id=super_admin_id,
            action=f"Updated Admin: {admin.name}",
            target_type="admin",
            target_id=admin_id
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"message": "Admin updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =========================================================
# DELETE ADMIN
# =========================================================
@bp.route("/admin/<int:admin_id>", methods=["DELETE"])
@jwt_required()
def delete_admin(admin_id):
    try:
        # Verify super admin
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401

        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        # Delete admin
        admin_name = admin.name
        db.session.delete(admin)
        db.session.commit()

        # Log activity
        log = ActivityLog(
            actor_role=UserRole.SUPER_ADMIN,
            actor_id=super_admin_id,
            action=f"Deleted Admin: {admin_name}",
            target_type="admin",
            target_id=admin_id
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"message": "Admin deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/admin/<int:admin_id>/users", methods=["GET"])
@jwt_required()
def get_admin_users(admin_id):
    try:
        super_admin_id = get_jwt_identity()
        if not SuperAdmin.query.get(super_admin_id):
            return jsonify({"error": "Unauthorized"}), 401
        
        users = User.query.filter_by(admin_id=admin_id).all()
        result = []
        for u in users:
            result.append({
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None
            })
            
        return jsonify({"users": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500