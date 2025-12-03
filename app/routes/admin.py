# admin.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from datetime import datetime, timezone
from ..models import db, Admin, User, Attendance, CallHistory, ActivityLog, UserRole
import re
from sqlalchemy import func

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# -------------------------
# Helpers
# -------------------------
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def validate_email(email: str) -> bool:
    return bool(email and EMAIL_PATTERN.match(email))


def iso(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    # ensure timezone-aware if possible
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return str(dt)


def admin_required():
    """
    Simple helper that checks the JWT contains role=admin.
    Call inside route handlers after jwt_required() by checking get_jwt().
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return False
    return True


def get_admin_or_401():
    """
    Fetch admin from JWT identity and check active/expiry.
    Returns (admin, response) where response is None when OK, otherwise a Flask response tuple.
    """
    try:
        admin_id = int(get_jwt_identity())
    except Exception:
        return None, (jsonify({"error": "Invalid token identity"}), 401)

    admin = Admin.query.get(admin_id)
    if not admin:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    if not admin.is_active:
        return None, (jsonify({"error": "Account deactivated"}), 403)
    if callable(getattr(admin, "is_expired", None)) and admin.is_expired():
        return None, (jsonify({"error": "Account expired"}), 403)
    return admin, None


def paginate_query(query, serialize_fn):
    """
    Generic pagination helper. Reads ?page & ?per_page from request.
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", 25))
    except ValueError:
        per_page = 25
    per_page = max(1, min(per_page, 200))  # bound per_page

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = [serialize_fn(item) for item in pagination.items]
    meta = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }
    return items, meta


def calculate_performance_for_user(user_id):
    """
    Example heuristic for performance_score:
      - attendance punctuality: % of on-time check-ins (status == 'on-time') * 0.6
      - call responsiveness: fraction of outgoing calls answered (duration > 0) * 0.4
    Returns a rounded 0-100 score.
    Adjust this function to match your desired business logic.
    """
    # attendance punctuality
    total_att = db.session.query(func.count(Attendance.id)).filter(Attendance.user_id == user_id).scalar() or 0
    ontime_att = db.session.query(func.count(Attendance.id)).filter(
        Attendance.user_id == user_id, Attendance.status == "on-time"
    ).scalar() or 0

    att_score = (ontime_att / total_att * 100) if total_att else 0

    # call responsiveness
    total_calls = db.session.query(func.count(CallHistory.id)).filter(CallHistory.user_id == user_id).scalar() or 0
    answered_calls = db.session.query(func.count(CallHistory.id)).filter(
        CallHistory.user_id == user_id, CallHistory.duration > 0
    ).scalar() or 0

    call_score = (answered_calls / total_calls * 100) if total_calls else 0

    # combine
    combined = (att_score * 0.6) + (call_score * 0.4)
    return round(combined, 2)


# -------------------------
# ADMIN LOGIN (unchanged mostly)
# -------------------------
@bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        admin = Admin.query.filter(func.lower(Admin.email) == func.lower(email)).first()

        if not admin or not admin.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        if not admin.is_active:
            return jsonify({"error": "Account deactivated"}), 403

        if callable(getattr(admin, "is_expired", None)) and admin.is_expired():
            return jsonify({"error": "Account expired"}), 403

        # Track last login
        admin.last_login = datetime.utcnow()
        db.session.commit()

        token = create_access_token(
            identity=str(admin.id),
            additional_claims={"role": "admin"}
        )

        return jsonify({
            "access_token": token,
            "user": {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "role": "admin",
                "user_limit": getattr(admin, "user_limit", None),
                "expiry_date": iso(getattr(admin, "expiry_date", None))
            }
        }), 200

    except Exception as e:
        current_app.logger.exception("Admin login error")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# CREATE USER (secure & transactional)
# -------------------------
@bp.route("/create-user", methods=["POST"])
@jwt_required()
def create_user():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        phone = data.get("phone")

        if not name or not email or not password:
            return jsonify({"error": "name, email and password are required"}), 400

        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400

        # user limit check
        total_users = User.query.filter_by(admin_id=admin.id).count()
        if getattr(admin, "user_limit", None) is not None and total_users >= admin.user_limit:
            return jsonify({"error": "User limit reached"}), 400

        if User.query.filter(func.lower(User.email) == email).first():
            return jsonify({"error": "Email already taken"}), 400

        user = User(
            name=name,
            email=email,
            phone=phone,
            admin_id=admin.id,
            created_at=datetime.utcnow()
        )
        user.set_password(password)

        # Activity log
        log = ActivityLog(
            actor_role=UserRole.ADMIN,
            actor_id=admin.id,
            action=f"Created user {email}",
            target_type="user"
        )

        db.session.add(user)
        # flush to get user.id for log target_id
        db.session.flush()
        log.target_id = user.id
        db.session.add(log)
        db.session.commit()

        return jsonify({"message": "User created", "user_id": user.id}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Create user failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# GET ALL USERS (with pagination)
# -------------------------
@bp.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        query = User.query.filter_by(admin_id=admin.id)

        # Search filter
        search = request.args.get("search", "").strip()
        if search:
            term = f"%{search}%"
            query = query.filter(
                (User.name.ilike(term)) | (User.email.ilike(term))
            )

        # Status filter
        status = request.args.get("status", "all")
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "inactive":
            query = query.filter(User.is_active == False)

        query = query.order_by(User.created_at.desc())

        def serialize(u):
            return {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "is_active": u.is_active,
                "performance_score": getattr(u, "performance_score", None),
                "created_at": iso(getattr(u, "created_at", None)),
                "last_login": iso(getattr(u, "last_login", None)),
                "last_sync": iso(getattr(u, "last_sync", None)),
                "has_sync_data": bool(getattr(u, "last_sync", None))
            }

        items, meta = paginate_query(query, serialize)
        return jsonify({"users": items, "meta": meta}), 200

    except Exception as e:
        current_app.logger.exception("Get users failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# DASHBOARD STATS (aggregate)
# -------------------------
@bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        users = User.query.filter_by(admin_id=admin.id).all()
        total = len(users)
        active = sum(1 for u in users if u.is_active)
        synced = sum(1 for u in users if u.last_sync)
        expired = sum(1 for u in users if callable(getattr(u, "is_expired", None)) and u.is_expired())

        # compute average performance (recalc if None)
        perf_values = []
        for u in users:
            if getattr(u, "performance_score", None) is None:
                score = calculate_performance_for_user(u.id)
                # optionally persist: u.performance_score = score
            else:
                score = u.performance_score
            perf_values.append(score or 0)

        avg_perf = round(sum(perf_values) / total, 2) if total else 0

        # Basic trend placeholder (you can compute time-series from ActivityLog)
        performance_trend = perf_values[-7:] if len(perf_values) >= 7 else perf_values

        return jsonify({
            "stats": {
                "total_users": total,
                "active_users": active,
                "expired_users": expired,
                "user_limit": admin.user_limit,
                "remaining_slots": (admin.user_limit - total) if admin.user_limit is not None else None,
                "users_with_sync": synced,
                "sync_rate": round((synced / total) * 100, 2) if total else 0,
                "avg_performance": avg_perf,
                "performance_trend": performance_trend
            }
        }), 200

    except Exception as e:
        current_app.logger.exception("Dashboard stats failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# RECENT 10 USER SYNC (paginated)
# -------------------------
@bp.route("/recent-sync", methods=["GET"])
@jwt_required()
def recent_sync():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        query = User.query.filter_by(admin_id=admin.id).filter(User.last_sync.isnot(None)).order_by(User.last_sync.desc())
        def serialize(u):
            return {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "last_sync": iso(getattr(u, "last_sync", None))
            }

        items, meta = paginate_query(query, serialize)
        return jsonify({"recent_sync": items, "meta": meta}), 200

    except Exception as e:
        current_app.logger.exception("Recent sync failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# USER ATTENDANCE (admin-wide listing, paginated)
# -------------------------
# @bp.route("/attendance", methods=["GET"])
@jwt_required()
def admin_attendance():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        # Join Attendance with User limited to this admin
        query = db.session.query(Attendance, User).join(User, Attendance.user_id == User.id).filter(User.admin_id == admin.id).order_by(Attendance.created_at.desc())

        # We will paginate by Attendance.id grouping - but for simplicity we paginate on the ORM result with flask_sqlalchemy paginate helper:
        # convert to subquery of Attendance IDs matching admin's users
        att_q = Attendance.query.join(User, Attendance.user_id == User.id).filter(User.admin_id == admin.id).order_by(Attendance.created_at.desc())
        def serialize(a):
            return {
                "id": a.id,
                "user_id": a.user_id,
                "user_name": getattr(a, "user").name if getattr(a, "user", None) else None,
                "check_in": iso(getattr(a, "check_in", None)),
                "check_out": iso(getattr(a, "check_out", None)),
                "status": a.status,
                "address": a.address,
                "created_at": iso(getattr(a, "created_at", None))
            }

        items, meta = paginate_query(att_q, serialize)
        return jsonify({"attendance": items, "meta": meta}), 200

    except Exception as e:
        current_app.logger.exception("Admin attendance failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# USER CALL HISTORY (ownership checked + pagination)
# -------------------------
@bp.route("/user-call-history/<int:user_id>", methods=["GET"])
@jwt_required()
def user_call_history(user_id):
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    # Ownership check
    user = User.query.get(user_id)
    if not user or user.admin_id != admin.id:
        return jsonify({"error": "Unauthorized user access"}), 403

    try:
        q = CallHistory.query.filter_by(user_id=user_id).order_by(CallHistory.timestamp.desc())

        def serialize(c):
            return {
                "id": c.id,
                "number": c.number,
                "call_type": c.call_type,
                "timestamp": iso(getattr(c, "timestamp", None)),
                "duration": c.duration,
                "name": c.name,
                "created_at": iso(getattr(c, "created_at", None))
            }

        items, meta = paginate_query(q, serialize)
        return jsonify({"call_history": items, "meta": meta}), 200

    except Exception as e:
        current_app.logger.exception("User call history failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# USER ATTENDANCE FULL LIST (ownership checked + pagination)
# -------------------------
@bp.route("/user-attendance/<int:user_id>", methods=["GET"])
@jwt_required()
def user_attendance(user_id):
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    user = User.query.get(user_id)
    if not user or user.admin_id != admin.id:
        return jsonify({"error": "Unauthorized user access"}), 403

    try:
        q = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.created_at.desc())

        def serialize(a):
            return {
                "id": a.id,
                "user_id": a.user_id,
                "check_in": iso(getattr(a, "check_in", None)),
                "check_out": iso(getattr(a, "check_out", None)),
                "status": a.status,
                "address": a.address,
                "created_at": iso(getattr(a, "created_at", None))
            }

        items, meta = paginate_query(q, serialize)
        return jsonify({"attendance": items, "meta": meta}), 200

    except Exception as e:
        current_app.logger.exception("User attendance failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# USER ANALYTICS (new feature)
# -------------------------
@bp.route("/user-analytics/<int:user_id>", methods=["GET"])
@jwt_required()
def user_analytics(user_id):
    """
    Returns analytics for a user:
      - total_calls, answered_calls, avg_call_duration
      - total_attendance, on_time_rate
      - last_sync, last_login
      - computed performance_score (and breakdown)
    """
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    user = User.query.get(user_id)
    if not user or user.admin_id != admin.id:
        return jsonify({"error": "Unauthorized user access"}), 403

    try:
        # Calls
        call_stats = db.session.query(
            func.count(CallHistory.id).label("total_calls"),
            func.sum(func.case([(CallHistory.duration > 0, 1)], else_=0)).label("answered_calls"),
            func.avg(CallHistory.duration).label("avg_duration")
        ).filter(CallHistory.user_id == user_id).one()

        total_calls = int(call_stats.total_calls or 0)
        answered_calls = int(call_stats.answered_calls or 0)
        avg_duration = float(call_stats.avg_duration or 0.0)

        # Attendance
        att_stats = db.session.query(
            func.count(Attendance.id).label("total_att"),
            func.sum(func.case([(Attendance.status == "on-time", 1)], else_=0)).label("on_time")
        ).filter(Attendance.user_id == user_id).one()

        total_att = int(att_stats.total_att or 0)
        on_time = int(att_stats.on_time or 0)
        on_time_rate = round((on_time / total_att) * 100, 2) if total_att else 0.0

        # last sync & login
        last_sync = getattr(user, "last_sync", None)
        last_login = getattr(user, "last_login", None)

        # computed performance
        perf_score = calculate_performance_for_user(user_id)

        analytics = {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "calls": {
                "total_calls": total_calls,
                "answered_calls": answered_calls,
                "avg_duration_seconds": round(avg_duration, 2)
            },
            "attendance": {
                "total_attendance": total_att,
                "on_time_count": on_time,
                "on_time_rate_percent": on_time_rate
            },
            "last_sync": iso(last_sync),
            "last_login": iso(last_login),
            "performance": {
                "score": perf_score,
                "method": "attendance(60%) + calls(40%) heuristic"
            }
        }

        return jsonify({"analytics": analytics}), 200

    except Exception as e:
        current_app.logger.exception("User analytics failed")
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# OPTIONAL: Endpoint to recalc & persist performance for all users (admin only)
# -------------------------
@bp.route("/recalc-performance", methods=["POST"])
@jwt_required()
def recalc_performance_all():
    if not admin_required():
        return jsonify({"error": "Admin role required"}), 403

    admin, resp = get_admin_or_401()
    if resp:
        return resp

    try:
        users = User.query.filter_by(admin_id=admin.id).all()
        updated = []
        for u in users:
            score = calculate_performance_for_user(u.id)
            u.performance_score = score
            updated.append({"user_id": u.id, "performance_score": score})

        db.session.commit()
        return jsonify({"message": "Performance recalculated", "updated": updated}), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Recalc performance failed")
        return jsonify({"error": "Internal server error"}), 500