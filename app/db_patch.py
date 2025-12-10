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
            'check_out_image': 'VARCHAR(1024)'
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
            
            conn.commit()
            print("Schema patch complete.")
            
    except Exception as e:
        print(f"Schema patch failed: {e}")
