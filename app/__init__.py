from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import (
    JWTManager,
    verify_jwt_in_request,
    get_jwt,
    get_jwt_identity,
)
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import inspect
from datetime import datetime, date
import os

from app.models import db, bcrypt, Admin, User, SuperAdmin
from config import Config

jwt = JWTManager()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # =======================================================
    # GLOBAL SUBSCRIPTION CHECKER
    # =======================================================
    @app.before_request
    def global_subscription_checker():

        if request.method == "OPTIONS":
            return

        try:
            verify_jwt_in_request(optional=True)
        except:
            return  # Ignore if no token

        identity = get_jwt_identity()
        if not identity:
            return

        claims = get_jwt()
        role = claims.get("role")
        today = datetime.utcnow().date()

        # -------- ADMIN CHECK --------
        if role == "admin":
            admin = Admin.query.get(int(identity))
            if admin and admin.expiry_date:
                expiry = (
                    admin.expiry_date.date()
                    if isinstance(admin.expiry_date, datetime)
                    else admin.expiry_date
                )
                if expiry < today:
                    return jsonify({"error": "Admin subscription expired"}), 403

        # -------- USER CHECK --------
        if role == "user":
            user = User.query.get(int(identity))
            if not user:
                return jsonify({"error": "Invalid user"}), 403

            admin = Admin.query.get(user.admin_id)

            if admin and admin.expiry_date:
                expiry = (
                    admin.expiry_date.date()
                    if isinstance(admin.expiry_date, datetime)
                    else admin.expiry_date
                )
                if expiry < today:
                    return jsonify({"error": "Your admin subscription has expired"}), 403

        return

    # =======================================================
    # IMPORT ROUTES
    # =======================================================

    from app.routes.super_admin import bp as super_admin_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.users import bp as users_bp
    from app.routes.fix import bp as fix_bp
    from app.routes.attendance import bp as attendance_bp
    from app.routes.call_history import bp as call_history_bp
    from app.routes.admin_call_history import bp as admin_call_history_bp
    from app.routes.admin_attendance import bp as admin_attendance_bp
    from app.routes.admin_call_analytics import bp as admin_call_analytics_bp

    from app.routes.admin_performance import bp as admin_performance_bp
    from app.routes.admin_dashboard import admin_dashboard_bp
    from app.routes.admin_sync import bp as admin_sync_bp
    from app.routes.call_analytics import bp as call_analytics_bp  # NEW

    # =======================================================
    # REGISTER BLUEPRINTS
    # =======================================================

    app.register_blueprint(super_admin_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(fix_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(call_history_bp)

    app.register_blueprint(admin_call_history_bp)
    app.register_blueprint(admin_attendance_bp)
    app.register_blueprint(admin_call_analytics_bp)
    app.register_blueprint(admin_performance_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(admin_sync_bp)

    app.register_blueprint(call_analytics_bp)  # NEW

    # =======================================================
    # DATABASE INIT
    # =======================================================
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.get_table_names():
            db.create_all()

    # =======================================================
    # FRONTEND ROUTING
    # =======================================================

    FRONTEND = os.path.abspath(os.path.join(os.getcwd(), "frontend"))

    @app.route("/")
    def home():
        return jsonify({"status": "running"})

    @app.route("/api/health")
    def health():
        return jsonify({"status": "running", "db": "connected"}), 200

    # -------- ADMIN FRONTEND --------
    @app.route("/admin/login.html")
    def admin_login_page():
        return send_from_directory(os.path.join(FRONTEND, "admin"), "login.html")

    @app.route("/admin/<path:filename>")
    def admin_static(filename):
        return send_from_directory(os.path.join(FRONTEND, "admin"), filename)

    # -------- SUPER ADMIN FRONTEND --------
    @app.route("/super_admin/login.html")
    def super_admin_login_page():
        return send_from_directory(os.path.join(FRONTEND, "super_admin"), "login.html")

    @app.route("/super_admin/<path:filename>")
    def super_admin_static(filename):
        return send_from_directory(os.path.join(FRONTEND, "super_admin"), filename)

    return app
