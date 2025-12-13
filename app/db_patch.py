from app.models import db
from sqlalchemy import text, inspect

def run_schema_patch():
    """
    Checks for missing columns and adds them via raw SQL.
    Safe to run on every startup (idempotent).
    """
    try:
        print("Running schema patcher...")
        engine = db.engine
        inspector = inspect(engine)
        
        # Check if table exists first
        if 'attendances' not in inspector.get_table_names():
            return
            
        columns = [c['name'] for c in inspector.get_columns('attendances')]
        
        # Columns to add
        new_columns = {
            'check_out_latitude': 'FLOAT',
            'check_out_longitude': 'FLOAT',
            'check_out_address': 'VARCHAR(500)',
            'check_out_image': 'VARCHAR(1024)',
            'current_session_id': 'VARCHAR(100)' # For single device login
        }
        
        with engine.connect() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    print(f"Adding missing column: {col_name} ({col_type})")
                    try:
                        # Use text() for safety
                        conn.execute(text(f'ALTER TABLE attendances ADD COLUMN {col_name} {col_type}'))
                        print(f"✅ Added {col_name}")
                    except Exception as e:
                        print(f"❌ Failed to add {col_name}: {e}")
            

            # Message for attendances
            # Now check USERS table for session_id
            if 'users' in inspector.get_table_names():
                user_cols = [c['name'] for c in inspector.get_columns('users')]
                if 'current_session_id' not in user_cols:
                    print("Adding current_session_id to users table...")
                    try:
                         conn.execute(text('ALTER TABLE users ADD COLUMN current_session_id VARCHAR(100)'))
                         print("✅ Added current_session_id to users")
                    except Exception as e:
                         print(f"❌ Failed to add current_session_id: {e}")

            # CALL HISTORY - recording_path
            if 'call_history' in inspector.get_table_names():
                ch_cols = [c['name'] for c in inspector.get_columns('call_history')]
                if 'recording_path' not in ch_cols:
                    print("Adding recording_path to call_history table...")
                    try:
                         conn.execute(text('ALTER TABLE call_history ADD COLUMN recording_path VARCHAR(1024)'))
                         print("✅ Added recording_path to call_history")
                    except Exception as e:
                         print(f"❌ Failed to add recording_path: {e}")

            conn.commit()
            
            # Create password_resets table if missing
            if 'password_resets' not in inspector.get_table_names():
                print("Creating password_resets table...")
                try:
                    conn.execute(text('''
                        CREATE TABLE password_resets (
                            id SERIAL PRIMARY KEY,
                            email VARCHAR(150) NOT NULL,
                            token VARCHAR(100) UNIQUE NOT NULL,
                            expires_at TIMESTAMP NOT NULL,
                            used BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    # Add index on email for faster lookups
                    conn.execute(text('CREATE INDEX idx_pwd_reset_email ON password_resets (email)'))
                    print("✅ Created password_resets table")
                except Exception as e:
                    print(f"❌ Failed to create password_resets table: {e}")

            conn.commit()
            print("Schema patch complete.")
            
    except Exception as e:
        print(f"Schema patch failed: {e}")
