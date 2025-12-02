# app/routes/attendance.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Attendance
from datetime import datetime
import uuid

bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")


def ts_to_datetime(value):
    """Convert milliseconds timestamp safely."""
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000)
    except:
        return None


@bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_attendance():
    try:
        data = request.get_json()

        if not data or "records" not in data:
            return jsonify({"error": "Invalid request format"}), 400

        user_id = int(get_jwt_identity())
        records = data["records"]

        for rec in records:
            try:
                external_id = rec.get("id")  # mobile-side ID

                # Parse timestamps to UTC
                check_in = ts_to_datetime(rec.get("check_in"))
                check_out = ts_to_datetime(rec.get("check_out"))

                # Check if record already exists
                existing = None
                if external_id:
                    existing = Attendance.query.filter_by(
                        external_id=external_id,
                        user_id=user_id
                    ).first()

                if existing:
                    # UPDATE existing
                    existing.check_in = check_in
                    existing.check_out = check_out
                    existing.latitude = rec.get("latitude")
                    existing.longitude = rec.get("longitude")
                    existing.address = rec.get("location")
                    existing.image_path = rec.get("imagePath")
                    existing.status = rec.get("status", "present")
                    existing.synced = True
                    existing.sync_timestamp = datetime.utcnow()

                else:
                    # INSERT new
                    new_rec = Attendance(
                        id = uuid.uuid4().hex,
                        external_id = external_id,
                        user_id = user_id,
                        check_in = check_in,
                        check_out = check_out,
                        latitude = rec.get("latitude"),
                        longitude = rec.get("longitude"),
                        address = rec.get("location"),
                        image_path = rec.get("imagePath"),
                        status = rec.get("status", "present"),
                        synced = True,
                        sync_timestamp = datetime.utcnow()
                    )
                    db.session.add(new_rec)
            except Exception as e:
                print(f"Error processing attendance record: {e}")
                continue

        db.session.commit()

        return jsonify({"status": "success", "message": "Attendance synced"}), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500