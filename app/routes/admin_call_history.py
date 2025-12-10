# app/routes/admin_call_history.py

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from app.models import db, User, CallHistory, Attendance
from sqlalchemy import or_, func, case
import io

# Optional: ReportLab for PDF
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

bp = Blueprint("admin_all_call_history", __name__, url_prefix="/api/admin")


from functools import wraps

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if get_jwt().get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


@bp.route("/all-call-history", methods=["GET"])
@jwt_required()
@admin_required
def all_call_history():
    try:
        admin_id = int(get_jwt_identity())

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))

        # ============================
        # 1️⃣ DATE FILTER
        # ============================
        filter_type = request.args.get("filter")  # today / week / month
        custom_date = request.args.get("date", "").strip()  # YYYY-MM-DD format
        
        now = datetime.utcnow()
        start_time = None

        if filter_type == "today":
            start_time = datetime(now.year, now.month, now.day)
        elif filter_type == "week":
            start_time = now - timedelta(days=7)
        elif filter_type == "month":
            start_time = now - timedelta(days=30)
        # Removed automatic 7-day default to show all available data
        # Users can explicitly apply filters if needed

        # ============================
        # 2️⃣ PHONE SEARCH FILTER
        # ============================
        search = request.args.get("search")
        
        # ============================
        # 3️⃣ CALL TYPE FILTER
        # ============================
        call_type = request.args.get("call_type")  # incoming/outgoing/missed

        # ============================
        # 4️⃣ USER FILTER
        # ============================
        user_id = request.args.get("user_id")
        if user_id and user_id != "all":
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None
        else:
            user_id = None

        # ============================
        # 6️⃣ BASE QUERY (JOIN + ADMIN FILTER)
        # ============================
        query = (
            db.session.query(CallHistory, User)
            .join(User, CallHistory.user_id == User.id)
            .filter(User.admin_id == admin_id)
        )

        # Apply date filter
        if custom_date:
            try:
                # Use explicit string range for maximum compatibility
                # This ensures we cover the entire day regardless of object types
                start_date_str = f"{custom_date} 00:00:00"
                end_date_str = f"{custom_date} 23:59:59"
                query = query.filter(CallHistory.timestamp >= start_date_str, CallHistory.timestamp <= end_date_str)
            except Exception:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # New Month Filter (YYYY-MM)
        month_param = request.args.get("month")
        if month_param:
            try:
                # Parse YYYY-MM
                part_year, part_month = map(int, month_param.split('-'))
                
                # Start of month
                start_dt = datetime(part_year, part_month, 1)
                
                # End of month (start of next month)
                if part_month == 12:
                    end_dt = datetime(part_year + 1, 1, 1)
                else:
                    end_dt = datetime(part_year, part_month + 1, 1)
                
                query = query.filter(CallHistory.timestamp >= start_dt, CallHistory.timestamp < end_dt)
            except ValueError:
                return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400

        elif start_time:
            query = query.filter(CallHistory.timestamp >= start_time)

        # Apply phone number search
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    CallHistory.phone_number.ilike(search_term),
                    CallHistory.formatted_number.ilike(search_term),
                    func.lower(CallHistory.contact_name).like(search_term)
                )
            )

        # Apply call type filter
        if call_type:
            query = query.filter(func.lower(CallHistory.call_type) == call_type.lower())

        # Apply user filter
        if user_id:
            query = query.filter(CallHistory.user_id == user_id)

        # Sorting
        query = query.order_by(CallHistory.timestamp.desc())

        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        # ============================
        # 6️⃣ STATS CALCULATION (For Modal Header)
        # ============================
        # Re-using logic from admin_performance.py for consistency
        # Calculate Work Time, Active, Inactive for the filtered period
        
        # Fetch Attendance for this User & Period
        # We need the same start_time / end_time logic used for the query
        stats_start = start_time
        stats_end = None
        
        # If no specific start time (e.g. 'all'), we might want to bound it or fetch all.
        # But 'query' (CallHistory) handles it. We need explicit range for Attendance query.
        
        attendances = []
        if stats_start:
             att_q = Attendance.query.filter(Attendance.user_id == user_id, Attendance.check_in >= stats_start)
             # Handle end range if applicable (e.g. month end)
             # The existing code for month filter logic (lines 106-123) sets query filter directly.
             # We need to replicate or extract that date range.
             
             # Re-determining the effective date range from request params:
             daterange_start = None
             daterange_end = None
             
             if custom_date:
                 daterange_start = datetime.strptime(custom_date, "%Y-%m-%d")
                 daterange_end = daterange_start + timedelta(days=1)
             elif month_param:
                 y, m = map(int, month_param.split('-'))
                 daterange_start = datetime(y, m, 1)
                 if m == 12: daterange_end = datetime(y+1, 1, 1)
                 else: daterange_end = datetime(y, m+1, 1)
             elif filter_type == "today":
                 now_ts = datetime.utcnow()
                 daterange_start = datetime(now_ts.year, now_ts.month, now_ts.day)
                 daterange_end = daterange_start + timedelta(days=1)
             elif filter_type == "week":
                 daterange_start = datetime.utcnow() - timedelta(days=7)
                 daterange_end = datetime.utcnow()
             elif filter_type == "month":
                 daterange_start = datetime.utcnow() - timedelta(days=30)
                 daterange_end = datetime.utcnow()
                 
             if daterange_start:
                att_q = Attendance.query.filter(Attendance.user_id == user_id, Attendance.check_in >= daterange_start)
                if daterange_end:
                    att_q = att_q.filter(Attendance.check_in < daterange_end)
                attendances = att_q.all()
        elif user_id:
             # All time for user
             attendances = Attendance.query.filter_by(user_id=user_id).all()

        # Calculate Stats
        total_active_sec = 0.0
        total_inactive_sec = 0.0
        total_work_sec = 0.0
        
        if attendances:
            # Group by day
            daily_data = {}
            for att in attendances:
                d_str = att.check_in.date().isoformat()
                if d_str not in daily_data:
                    daily_data[d_str] = {"check_in": att.check_in, "check_out": att.check_out, "calls": []}
                else:
                    if att.check_in < daily_data[d_str]["check_in"]:
                        daily_data[d_str]["check_in"] = att.check_in
                    current_co = daily_data[d_str]["check_out"]
                    if att.check_out:
                         if current_co is None or att.check_out > current_co:
                             daily_data[d_str]["check_out"] = att.check_out

            # Fetch ALL calls for stats (not just paginated ones)
            # Re-run a simplified query for stats
            calls_q = CallHistory.query.filter_by(user_id=user_id)
            if daterange_start:
                calls_q = calls_q.filter(CallHistory.timestamp >= daterange_start)
                if daterange_end:
                    calls_q = calls_q.filter(CallHistory.timestamp < daterange_end)
            
            # Additional filters (phone/type) should arguably apply to call history list NOT work performance?
            # Performance is usually about ALL activity. Let's ignore search/type filters for "Work Time" calc.
            all_calls_for_stats = calls_q.order_by(CallHistory.timestamp.asc()).all()

            for call in all_calls_for_stats:
                d_str = call.timestamp.date().isoformat()
                if d_str in daily_data:
                    daily_data[d_str]["calls"].append(call)

            def is_lunch_time(dt): return dt.hour == 13

            for d_str, day_info in daily_data.items():
                c_in = day_info["check_in"]
                c_out = day_info["check_out"]
                
                if c_out is None:
                    if d_str == datetime.utcnow().date().isoformat():
                        c_out = datetime.utcnow()
                    else: continue 

                session_dur = (c_out - c_in).total_seconds()
                work_dur = max(0, session_dur - 3600)
                total_work_sec += work_dur

                last_sync_time = c_in
                day_calls = day_info["calls"]
                
                for call in day_calls:
                    curr_time = call.timestamp
                    if curr_time < c_in: continue
                    if curr_time > c_out: continue
                    if is_lunch_time(curr_time):
                        last_sync_time = curr_time
                        continue
                    
                    raw_gap = (curr_time - last_sync_time).total_seconds()
                    
                    # Lunch overlap calc
                    lunch_start = c_in.replace(hour=13, minute=0, second=0, microsecond=0)
                    lunch_end = c_in.replace(hour=14, minute=0, second=0, microsecond=0)
                    overlap_start = max(last_sync_time, lunch_start)
                    overlap_end = min(curr_time, lunch_end)
                    overlap = max(0, (overlap_end - overlap_start).total_seconds())
                    
                    effective_gap = max(0, raw_gap - overlap)
                    
                    if effective_gap <= 600: total_active_sec += effective_gap
                    else: total_inactive_sec += effective_gap
                    last_sync_time = curr_time
                
                # Final Gap
                final_gap_raw = (c_out - last_sync_time).total_seconds()
                lunch_start = c_in.replace(hour=13, minute=0, second=0, microsecond=0)
                lunch_end = c_in.replace(hour=14, minute=0, second=0, microsecond=0)
                overlap_start = max(last_sync_time, lunch_start)
                overlap_end = min(c_out, lunch_end)
                overlap = max(0, (overlap_end - overlap_start).total_seconds())
                final_gap = max(0, final_gap_raw - overlap)
                
                if final_gap <= 600: total_active_sec += final_gap
                else: total_inactive_sec += final_gap

        # Check-in/out display (Earliest/Latest)
        overall_check_in = None
        overall_check_out = None
        if attendances:
            overall_check_in = min([a.check_in for a in attendances if a.check_in])
            outs = [a.check_out for a in attendances if a.check_out]
            if outs: overall_check_out = max(outs)

        stats = {
            "work_time": f"{round(total_work_sec/3600, 1)}h",
            "active_time": f"{round(total_active_sec/3600, 1)}h",
            "inactive_time": f"{round(total_inactive_sec/3600, 1)}h",
            "check_in": overall_check_in.strftime('%I:%M %p') if overall_check_in else "-",
            "check_out": overall_check_out.strftime('%I:%M %p') if overall_check_out else "-"
        }


        data = []
        for rec, user_obj in paginated.items:
            data.append({
                "id": rec.id,
                "user_id": rec.user_id,
                "user_name": user_obj.name,
                "phone_number": rec.phone_number,
                "formatted_number": rec.formatted_number,
                "contact_name": rec.contact_name,
                "call_type": rec.call_type,
                "duration": rec.duration,
                "timestamp": rec.timestamp.isoformat() if rec.timestamp else None,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            })

        return jsonify({
            "call_history": data,
            "stats": stats,
            "meta": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal error", "detail": str(e)}), 400


@bp.route("/download-user-history", methods=["GET"])
@jwt_required()
@admin_required
def download_user_history():
    """
    Generates and downloads a PDF report for a single user's call history.
    Values passed: user_id, filter (today, month, all)
    """
    if not HAS_REPORTLAB:
        return jsonify({"error": "PDF generation library (reportlab) not installed on server."}), 500

    try:
        admin_id = int(get_jwt_identity())
        user_id = request.args.get("user_id")
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Verify user exists and belongs to admin
        user = User.query.filter_by(id=user_id, admin_id=admin_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # ============================
        # 1️⃣ DATE FILTER SETUP
        # ============================
        filter_type = request.args.get("filter", "all")
        now = datetime.utcnow()
        start_time = None
        period_label = "All Time"

        if filter_type == "today":
            start_time = datetime(now.year, now.month, now.day)
            period_label = f"Today ({now.strftime('%d %b %Y')})"
        elif filter_type == "month":
            start_time = datetime(now.year, now.month, 1) # Start of current month
            period_label = f"Monthly ({now.strftime('%B %Y')})"
        
        # ============================
        # 2️⃣ QUERY DATA
        # ============================
        query = CallHistory.query.filter_by(user_id=user_id)
        
        if start_time:
            # For "month", we ideally want the whole month range, but the previous logic just used start_time >= X
            # Let's improve it for month to be cleaner
            if filter_type == "month":
                 if now.month == 12:
                     end_time = datetime(now.year + 1, 1, 1)
                 else:
                     end_time = datetime(now.year, now.month + 1, 1)
                 query = query.filter(CallHistory.timestamp >= start_time, CallHistory.timestamp < end_time)
            else:
                 query = query.filter(CallHistory.timestamp >= start_time)
        
        # Sort by latest
        calls = query.order_by(CallHistory.timestamp.desc()).all()

        # ============================
        # 3️⃣ GENERATE PDF
        # ============================
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=5,
            textColor=colors.HexColor('#2563EB')
        )
        elements.append(Paragraph("NxtCall.app", title_style))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.gray
        )
        elements.append(Paragraph(f"Report Period: {period_label}", subtitle_style))

        # Table Data
        # Columns: Type, Number, Duration, Date
        table_data = [[ "Type", "Number", "Duration", "Date & Time" ]]

        def fmt_dur(seconds):
             if not seconds: return "0s"
             h = seconds // 3600
             m = (seconds % 3600) // 60
             s = seconds % 60
             parts = []
             if h: parts.append(f"{h}h")
             if m: parts.append(f"{m}m")
             if s: parts.append(f"{s}s")
             return " ".join(parts)

        for c in calls:
            # Color coding for type (text only in PDF)
            c_type = c.call_type.capitalize()
            
            table_data.append([
                c_type,
                c.phone_number,
                fmt_dur(c.duration),
                c.timestamp.strftime('%Y-%m-%d %H:%M:%S') if c.timestamp else "-"
            ])

        if len(table_data) == 1:
            elements.append(Paragraph("No calls found for this period.", styles['Normal']))
        else:
            t = Table(table_data, colWidths=[80, 150, 80, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        
        filename = f"CallHistory_{user.name}_{filter_type}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal error generating report", "detail": str(e)}), 400