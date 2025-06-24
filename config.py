import os
import secrets
from datetime import timedelta

class BaseConfig:
    """Base configuration with modern 2025 security standards."""
    
    # Enhanced Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SECRET_KEY_FALLBACKS = [os.environ.get('SECRET_KEY_FALLBACK')] if os.environ.get('SECRET_KEY_FALLBACK') else []
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or secrets.token_hex(32)
    
    # Database Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 20
    }
    SQLALCHEMY_ECHO = False

    SESSION_COOKIE_NAME = 'football_session'
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    MAX_FORM_MEMORY_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_FORM_PARTS = 1000
    
    # Trusted hosts for security
    TRUSTED_HOSTS = os.environ.get('TRUSTED_HOSTS', '').split(',') if os.environ.get('TRUSTED_HOSTS') else []

    # Rate Limiting
    API_RATE_LIMIT = '100 per minute'
    RATELIMIT_STORAGE_URL = 'memory://'  # Can be changed to Redis later
    
    # Performance monitoring
    MONITORING_ENABLED = True
    MONITORING_INTERVAL = 60  # seconds
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Caching Configuration
    CACHE_TYPE = 'simple'  # Will be upgraded to Redis in production
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'football_app:'
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[Football Manager] '
    MAIL_SENDER = os.environ.get('MAIL_SENDER', 'noreply@footballmanager.com')
    
    # Timezone Configuration
    TIMEZONE = 'Europe/Warsaw'
    
    # API Configuration
    API_VERSION = 'v1'
    API_TITLE = 'Football Manager API'
    
    # Modern Performance Settings
    TEMPLATES_AUTO_RELOAD = False
    EXPLAIN_TEMPLATE_LOADING = False
    
    # WebSocket Configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25
    
    # Feature Flags
    ENABLE_REAL_TIME_UPDATES = True
    ENABLE_PUSH_NOTIFICATIONS = True
    ENABLE_DARK_MODE = True
    ENABLE_PWA = True
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        pass

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///football_dev.db'
    CACHE_TYPE = 'simple'
    RATELIMIT_ENABLED = False
    TEMPLATES_AUTO_RELOAD = True

class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'simple'
    RATELIMIT_ENABLED = False
    
    # Override SQLAlchemy engine options for SQLite (no pooling)
    SQLALCHEMY_ENGINE_OPTIONS = {}

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///football.db'
    
    # Production caching with Redis
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)
        
        # Production logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler('logs/football.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Football Manager startup')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
