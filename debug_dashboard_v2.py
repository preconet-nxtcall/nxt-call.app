
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# 1. Read .env manualy
db_url = None
try:
    with open(".env", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.strip().split("=", 1)[1]
                # Fix postgres prefix for sqlalchemy
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                break
except Exception as e:
    print(f"Error reading .env: {e}")

if not db_url:
    print("Could not find DATABASE_URL in .env")
    # Fallback to os.environ if set
    db_url = os.environ.get("DATABASE_URL")

if not db_url:
    print("No DB URL found. Exiting.")
    sys.exit(1)

print(f"Connecting to DB: {db_url.split('@')[-1]}") # Hide password

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("\n--- CHECKING CALL HISTORY (Last 7 Days) ---")
        
        # Get raw calls using SQL for max reliability
        query = text("""
            SELECT id, user_id, timestamp, created_at 
            FROM call_history 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        result = conn.execute(query)
        rows = result.fetchall()
        
        print(f"Found {len(rows)} recent calls:")
        for r in rows:
            print(f"ID: {r.id} | User: {r.user_id} | TS: {r.timestamp} | Created: {r.created_at}")

        print("\n--- SIMULATING DASHBOARD LOGIC ---")
        # Logic: 
        # local_delta = +5.5h (assuming IST offset -330)
        local_delta = timedelta(hours=5, minutes=30)
        
        now_local = datetime.utcnow() + local_delta
        print(f"Now Local (IST): {now_local}")
        
        counts = {}
        for r in rows:
            if r.timestamp:
                # Convert
                # Note: valid DB timestamp is already datetime object usually
                ts = r.timestamp
                if isinstance(ts, str):
                     ts = datetime.fromisoformat(str(ts))
                
                local_dt = ts + local_delta
                d_key = str(local_dt.date())
                
                print(f"  -> Call {r.timestamp} UTC => {local_dt} IST => Key: {d_key}")
                counts[d_key] = counts.get(d_key, 0) + 1
        
        print(f"\nCounts Map: {counts}")
        
        # Check Today
        today_key = str(now_local.date())
        print(f"Today Key: {today_key} -> Count: {counts.get(today_key, 0)}")

except Exception as e:
    print(f"DB Error: {e}")
