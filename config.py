import os
import secrets
from datetime import timedelta

class BaseConfig:
    # Bezpieczeństwo
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or secrets.token_hex(32)
    
    # Baza danych
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 20
    }
    SQLALCHEMY_ECHO = False
    
    # Cache Redis/Memory (for future implementation)
    CACHE_TYPE = 'simple'  # Can be changed to 'redis' later
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Sesja
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Logowanie
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Rate limiting
    LOGIN_RATE_LIMIT = '5 per minute'
    API_RATE_LIMIT = '100 per minute'
    RATELIMIT_STORAGE_URL = 'memory://'  # Can be changed to Redis later
    
    # Performance monitoring
    MONITORING_ENABLED = True
    MONITORING_INTERVAL = 60  # seconds
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///football_dev.db'
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///football_test.db'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///football.db'
    LOG_LEVEL = 'WARNING'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 