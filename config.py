import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
    
    # Notification Config
    ZEPTOMAIL_USER = os.environ.get("ZEPTOMAIL_USER", "")
    ZEPTOMAIL_API_TOKEN = os.environ.get("ZEPTOMAIL_API_TOKEN", "")
