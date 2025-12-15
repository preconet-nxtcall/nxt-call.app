# #!/usr/bin/env bash
# echo "🚀 Starting build process..."

# # Install dependencies
# pip install -r requirements.txt

# # Create all tables in the connected database
# python - <<'PYCODE'
# from app import create_app
# from app.models import db, SuperAdmin
# from sqlalchemy import inspect

# app = create_app()
# with app.app_context():
#     print("⚙️ Checking database connection and tables...")

#     inspector = inspect(db.engine)
#     existing_tables = inspector.get_table_names()
#     print(f"📋 Existing tables before creation: {existing_tables}")

#     # Create tables if not present
#     db.create_all()
#     print("✅ Tables created successfully!")

#     # Ensure default SuperAdmin exists
#     if not SuperAdmin.query.first():
#         super_admin = SuperAdmin(
#             name="Super Admin",
#             email="super@callmanager.com"
#         )
#         super_admin.set_password("admin123")
#         db.session.add(super_admin)
#         db.session.commit()
#         print("✅ Default Super Admin created: super@callmanager.com / admin123")
#     else:
#         print("ℹ️ Super Admin already exists.")
# PYCODE

# echo "✅ Build completed successfully!"


#!/usr/bin/env bash
#!/usr/bin/env bash
echo "🚀 Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Initialize database and create default SuperAdmin
python - <<'PYCODE'
from app import create_app
from app.models import db, SuperAdmin
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    print("⚙️ Checking database connection and tables...")
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    print(f"📋 Existing tables before creation: {existing_tables}")

    db.create_all()
    print("✅ Tables created successfully!")

    admin = SuperAdmin.query.first()
    if not admin:
        admin = SuperAdmin(
            name="Super Admin",
            email="nxtcall.app@gmail.com"
        )
        admin.set_password("kolkata@2025")
        db.session.add(admin)
        db.session.commit()
        print("✅ Default Super Admin created: nxtcall.app@gmail.com / kolkata@2025")
    else:
        # Force update for user request
        admin.email = "nxtcall.app@gmail.com"
        admin.set_password("kolkata@2025")
        db.session.commit()
        print("✅ Super Admin credentials updated to: nxtcall.app@gmail.com / kolkata@2025")

PYCODE

# Run constraint fixes
python db_fix_constraints.py

echo "✅ Build completed successfully!"
