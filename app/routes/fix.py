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
        out1 = fix_admin_table().json
        out2 = fix_attendance_table().json

        return jsonify({
            "message": "All fixes executed",
            "admin_table": out1,
            "attendance_table": out2
        }), 200

    except Exception as e:
        current_app.logger.exception("ALL fix error")
        return jsonify({"error": str(e)}), 500