# app/routes/attendance.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Attendance
from datetime import datetime
import uuid
import os
from werkzeug.utils import secure_filename
from PIL import Image

bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads", "attendance")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ts_to_datetime(value):
    """Convert milliseconds timestamp safely."""
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000)
    except:
        return None


@bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_image():
    """
    Uploads an image, compresses it to < 200KB, and returns the relative path.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Open image using Pillow
            img = Image.open(file)
            
            # Convert RGBA to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if too large (max width 1024px)
            max_width = 1024
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Compress and Save
            # Quality 85 is usually good, but we want < 200KB.
            # We can try saving with quality 70 first.
            img.save(filepath, "JPEG", quality=70, optimize=True)
            
            # Check size
            file_size = os.path.getsize(filepath)
            if file_size > 200 * 1024:
                # If still too big, compress more
                img.save(filepath, "JPEG", quality=50, optimize=True)

            # Return relative path for storage
            relative_path = f"uploads/attendance/{filename}"
            
            return jsonify({
                "status": "success",
                "image_path": relative_path,
                "message": "Image uploaded and compressed"
            }), 200

        except Exception as e:
            print(f"Image upload failed: {e}")
            return jsonify({"error": "Image processing failed"}), 500
    
    return jsonify({"error": "Invalid file type"}), 400


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
                    # Only update image_path if provided and not empty
                    if rec.get("imagePath"):
                        existing.image_path = rec.get("imagePath")
                    existing.status = rec.get("status", "present").lower()
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
                        status = rec.get("status", "present").lower(),
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