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
        stats = {
            "total_admins": Admin.query.count(),
            "active_admins": Admin.query.filter_by(is_active=True).count(),
            "expired_admins": Admin.query.filter(Admin.expiry_date < datetime.utcnow()).count(),
            "total_users": User.query.count(),
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
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()

        formatted = [
            {
                "id": log.id,
                "action": log.action,
                "actor_role": _safe_enum_value(log.actor_role),
                "actor_id": log.actor_id,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]

        return jsonify({"logs": formatted}), 200

    except Exception as e:
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