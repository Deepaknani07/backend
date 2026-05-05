import os


class Config:
    SQLALCHEMY_DATABASE_URI      = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY                   = os.environ.get('SECRET_KEY', 'qf-admin-secret-key-change-in-production')
    SESSION_COOKIE_HTTPONLY      = True
    SESSION_COOKIE_SAMESITE      = 'Lax'