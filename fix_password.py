from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    email = "mannanhossen5@gmail.com"
    user = User.query.filter_by(email=email).first()
    
    if user:
        print(f"Found user: {user.name} ({user.email})")
        user.set_password("user123")
        db.session.commit()
        print(f"Password for {email} has been reset to 'user123'")
    else:
        print(f"User with email {email} not found!")
