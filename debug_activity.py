
from app import create_app, db
from app.models import ActivityLog, UserRole
from datetime import datetime, timezone

app = create_app()

with app.app_context():
    print("Checking ActivityLog table...")
    try:
        count = ActivityLog.query.count()
        print(f"ActivityLog count: {count}")
        
        print("Checking recent activity query...")
        now_utc = datetime.utcnow()
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        logs = ActivityLog.query.filter(
            ActivityLog.actor_role == UserRole.ADMIN,
            ActivityLog.timestamp >= today_start
        ).all()
        print(f"Query successful. Found {len(logs)} logs.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
