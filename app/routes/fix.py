# app/routes/fix.py
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import inspect, text
from app.models import db

bp = Blueprint('fix', __name__, url_prefix='/api/fix')

# SECRET KEY REQUIRED TO RUN FIX (CHANGE & PUT IN .env)
SUPER_ADMIN_SECRET = "MANNAN_DB_FIX_2025"


# ----------------------------------------
# Role Checker
# ----------------------------------------
def admin_required():
    claims = get_jwt()
    return claims.get("role") == "admin"


# ----------------------------------------
# FIX ADMIN TABLE
# ----------------------------------------
@bp.route('/admin-table', methods=['POST'])
@jwt_required()
def fix_admin_table():
    """
    Fix missing columns in 'admins' table.
    Requires:
    - JWT with role=admin
    - super_admin_key in POST JSON
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('admins')]
        results = []

        def add_column_if_missing(col_name, ddl):
            if col_name not in columns:
                db.session.execute(text(ddl))
                results.append(f"Added column: {col_name}")
            else:
                results.append(f"Column already exists: {col_name}")

        # Columns to fix
        add_column_if_missing(
            "user_limit",
            "ALTER TABLE admins ADD COLUMN user_limit INTEGER DEFAULT 10;"
        )

        add_column_if_missing(
            "is_active",
            "ALTER TABLE admins ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"
        )

        add_column_if_missing(
            "last_login",
            "ALTER TABLE admins ADD COLUMN last_login TIMESTAMP;"
        )

        db.session.commit()

        return jsonify({
            "message": "Admin table check complete",
            "changes": results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Admin table fix error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# FIX ATTENDANCE TABLE
# ----------------------------------------
@bp.route('/attendance-table', methods=['POST'])
@jwt_required()
def fix_attendance_table():
    """
    Fix missing columns in 'attendances' table.
    Main fix: external_id column for sync.
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('attendances')]
        results = []

        def add_column_if_missing(col_name, ddl):
            if col_name not in columns:
                db.session.execute(text(ddl))
                results.append(f"Added column: {col_name}")
            else:
                results.append(f"Column already exists: {col_name}")

        # Add external_id (required for proper sync)
        add_column_if_missing(
            "external_id",
            "ALTER TABLE attendances ADD COLUMN external_id VARCHAR(64);"
        )

        # Add index on external_id (optional but recommended)
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_attendance_external_id ON attendances(external_id);")
        )

        db.session.commit()

        return jsonify({
            "message": "Attendance table check complete",
            "changes": results
        }), 200

# app/routes/fix.py
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import inspect, text
from app.models import db

bp = Blueprint('fix', __name__, url_prefix='/api/fix')

# SECRET KEY REQUIRED TO RUN FIX (CHANGE & PUT IN .env)
SUPER_ADMIN_SECRET = "MANNAN_DB_FIX_2025"


# ----------------------------------------
# Role Checker
# ----------------------------------------
def admin_required():
    claims = get_jwt()
    return claims.get("role") == "admin"


# ----------------------------------------
# FIX ADMIN TABLE
# ----------------------------------------
@bp.route('/admin-table', methods=['POST'])
@jwt_required()
def fix_admin_table():
    """
    Fix missing columns in 'admins' table.
    Requires:
    - JWT with role=admin
    - super_admin_key in POST JSON
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('admins')]
        results = []

        def add_column_if_missing(col_name, ddl):
            if col_name not in columns:
                db.session.execute(text(ddl))
                results.append(f"Added column: {col_name}")
            else:
                results.append(f"Column already exists: {col_name}")

        # Columns to fix
        add_column_if_missing(
            "user_limit",
            "ALTER TABLE admins ADD COLUMN user_limit INTEGER DEFAULT 10;"
        )

        add_column_if_missing(
            "is_active",
            "ALTER TABLE admins ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"
        )

        add_column_if_missing(
            "last_login",
            "ALTER TABLE admins ADD COLUMN last_login TIMESTAMP;"
        )

        db.session.commit()

        return jsonify({
            "message": "Admin table check complete",
            "changes": results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Admin table fix error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# FIX ATTENDANCE TABLE
# ----------------------------------------
@bp.route('/attendance-table', methods=['POST'])
@jwt_required()
def fix_attendance_table():
    """
    Fix missing columns in 'attendances' table.
    Main fix: external_id column for sync.
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('attendances')]
        results = []

        def add_column_if_missing(col_name, ddl):
            if col_name not in columns:
                db.session.execute(text(ddl))
                results.append(f"Added column: {col_name}")
            else:
                results.append(f"Column already exists: {col_name}")

        # Add external_id (required for proper sync)
        add_column_if_missing(
            "external_id",
            "ALTER TABLE attendances ADD COLUMN external_id VARCHAR(64);"
        )

        # Add index on external_id (optional but recommended)
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_attendance_external_id ON attendances(external_id);")
        )

        db.session.commit()

        return jsonify({
            "message": "Attendance table check complete",
            "changes": results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Attendance table fix error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# FIX ACTIVITY LOGS TABLE
# ----------------------------------------
@bp.route('/activity-logs-table', methods=['POST'])
@jwt_required()
def fix_activity_logs_table():
    """
    Fix missing columns in 'activity_logs' table.
    Main fix: extra_data column.
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('activity_logs')]
        results = []

        def add_column_if_missing(col_name, ddl):
            if col_name not in columns:
                db.session.execute(text(ddl))
                results.append(f"Added column: {col_name}")
            else:
                results.append(f"Column already exists: {col_name}")

        # Add extra_data
        add_column_if_missing(
            "extra_data",
            "ALTER TABLE activity_logs ADD COLUMN extra_data TEXT;"
        )

        db.session.commit()

        return jsonify({
            "message": "Activity Logs table check complete",
            "changes": results
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Activity Logs table fix error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# FIX ALL TABLES (OPTIONAL)
# ----------------------------------------
@bp.route('/all', methods=['POST'])
@jwt_required()
def fix_all_tables():
    """
    Run all fixes at once.
    """
    if not admin_required():
        return jsonify({"error": "Admin access only"}), 403

    body = request.get_json() or {}
    if body.get("super_admin_key") != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid super admin key"}), 403

    try:
        # We call the functions directly if they were refactored to not return Response objects immediately,
        # but since they are routes, we can't easily call them as functions without mocking request context.
        # So we will just duplicate logic or refactor. For safety/speed, let's just run the logic here.
        
        # 1. Admin Table
        inspector = inspect(db.engine)
        results = []
        
        # Admin
        admin_cols = [col['name'] for col in inspector.get_columns('admins')]
        if "user_limit" not in admin_cols:
            db.session.execute(text("ALTER TABLE admins ADD COLUMN user_limit INTEGER DEFAULT 10;"))
            results.append("Added user_limit to admins")
        if "is_active" not in admin_cols:
            db.session.execute(text("ALTER TABLE admins ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
            results.append("Added is_active to admins")
        if "last_login" not in admin_cols:
            db.session.execute(text("ALTER TABLE admins ADD COLUMN last_login TIMESTAMP;"))
            results.append("Added last_login to admins")

        # Attendance
        att_cols = [col['name'] for col in inspector.get_columns('attendances')]
        if "external_id" not in att_cols:
            db.session.execute(text("ALTER TABLE attendances ADD COLUMN external_id VARCHAR(64);"))
            results.append("Added external_id to attendances")
            
        # Activity Logs
        act_cols = [col['name'] for col in inspector.get_columns('activity_logs')]
        if "extra_data" not in act_cols:
            db.session.execute(text("ALTER TABLE activity_logs ADD COLUMN extra_data TEXT;"))
            results.append("Added extra_data to activity_logs")

        db.session.commit()

        return jsonify({
            "message": "All fixes executed",
            "changes": results
        }), 200

    except Exception as e:
        current_app.logger.exception("ALL fix error")
        return jsonify({"error": str(e)}), 500