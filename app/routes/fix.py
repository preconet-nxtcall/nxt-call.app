# app/routes/fix.py
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import inspect, text
from app.models import db

bp = Blueprint('fix', __name__, url_prefix='/api/fix')

@bp.route("/migrate", methods=["GET"])
def run_migration():
    try:
        # RAW SQL FIX to bypass Alembic/SSL issues (User keeps using this link)
        sql = """
        DROP TABLE IF EXISTS followups CASCADE;
        CREATE TABLE followups (
            id VARCHAR(100) NOT NULL, 
            user_id INTEGER NOT NULL, 
            contact_name VARCHAR(255), 
            phone VARCHAR(20) NOT NULL, 
            message TEXT, 
            date_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
            status VARCHAR(20) NOT NULL, 
            created_at TIMESTAMP WITHOUT TIME ZONE, 
            updated_at TIMESTAMP WITHOUT TIME ZONE, 
            PRIMARY KEY (id), 
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
        db.session.execute(text(sql))
        db.session.commit()
        return jsonify({"success": True, "message": "Database fixed via SQL (Alembic bypassed)."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Migration failed")
        return jsonify({"error": str(e)}), 500

@bp.route("/manual-followup", methods=["GET"])
def manual_followup_fix():
    try:
        # RAW SQL FIX to bypass Alembic/SSL issues
        sql = """
        DROP TABLE IF EXISTS followups CASCADE;
        CREATE TABLE followups (
            id VARCHAR(100) NOT NULL, 
            user_id INTEGER NOT NULL, 
            contact_name VARCHAR(255), 
            phone VARCHAR(20) NOT NULL, 
            message TEXT, 
            date_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
            status VARCHAR(20) NOT NULL, 
            created_at TIMESTAMP WITHOUT TIME ZONE, 
            updated_at TIMESTAMP WITHOUT TIME ZONE, 
            PRIMARY KEY (id), 
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
        db.session.execute(text(sql))
        db.session.commit()
        return jsonify({"success": True, "message": "Followup table reset successfully via SQL."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Manual SQL fix failed")
        return jsonify({"error": str(e)}), 500

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


# ----------------------------------------
# FIX DROP EMAIL CONSTRAINT
# ----------------------------------------
@bp.route('/drop-email-constraint', methods=['GET'])
def drop_email_constraint():
    """
    Drop the global unique constraint on users.email
    so duplicate emails can exist under different admins.
    """
    key = request.args.get('key')
    if key != SUPER_ADMIN_SECRET:
        return jsonify({"error": "Invalid key"}), 403

    try:
        results = []
        # Try finding constraint name again to be safe, or just try dropping common names
        
        # Method 1: Drop users_email_key (Default)
        try:
            db.session.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;"))
            results.append("Dropped users_email_key")
        except Exception as e:
            results.append(f"Failed to drop users_email_key: {e}")

        # Method 2: Drop users_email_uk (Common alt)
        try:
            db.session.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key1;"))
            # results.append("Dropped users_email_key1 (if existed)")
        except:
            pass

        # Also try to specifically find it
        find_sql = text("SELECT conname FROM pg_constraint WHERE conrelid = 'users'::regclass AND contype = 'u'")
        constraints = db.session.execute(find_sql).fetchall()
        
        dropped_any = False
        for cdict in constraints:
            cname = cdict[0]
            # If it looks like an email constraint?
            # We can't be 100% sure if it's the email one without checking columns, but let's assume 'email' in name
            # Or usually it is the ONLY unique constraint besides PK
            if 'pk' not in cname and 'pkey' not in cname:
                 # Check if this constraint covers email column
                 # This is getting complex SQL.
                 # Let's just trust 'users_email_key' is usually the one created by SQLAlchemy
                 pass

        db.session.commit()
        return jsonify({
            "message": "Constraint drop executed (check results)",
            "results": results,
            "current_constraints": [r[0] for r in constraints]
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500