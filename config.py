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
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 0
    }
    
    # Modern Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'football_session'
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    MAX_FORM_MEMORY_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_FORM_PARTS = 1000
    
    # Trusted hosts for security
    TRUSTED_HOSTS = os.environ.get('TRUSTED_HOSTS', '').split(',') if os.environ.get('TRUSTED_HOSTS') else []
    
    # Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Logging Configuration
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = '100 per hour'
    LOGIN_RATE_LIMIT = '5 per minute'
    API_RATE_LIMIT = '1000 per hour'
    
    # Caching Configuration
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
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
    SOCKETIO_ASYNC_MODE = 'eventlet'
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
    """Development configuration with debugging enabled."""
    
    DEBUG = True
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///football_dev.db'
    
    # Security (relaxed for development)
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True  # Keep CSRF protection even in development
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Caching (simple for development)
    CACHE_TYPE = 'simple'
    
    # Templates
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = True
    
    # Rate limiting (relaxed)
    RATELIMIT_ENABLED = False
    
    # Development tools
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

class TestingConfig(BaseConfig):
    """Testing configuration for automated tests."""
    
    TESTING = True
    DEBUG = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Security (disabled for testing)
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False
    
    # Caching
    CACHE_TYPE = 'null'
    
    # Logging
    LOG_LEVEL = 'CRITICAL'
    
    # Email testing
    MAIL_SUPPRESS_SEND = True
    
    # Performance
    TEMPLATES_AUTO_RELOAD = False

class ProductionConfig(BaseConfig):
    """Production configuration with enhanced security and performance."""
    
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///football.db'
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Performance optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # 1 hour
        'pool_size': 20,
        'max_overflow': 10
    }
    
    # Logging
    LOG_LEVEL = 'WARNING'
    
    # Enhanced rate limiting
    RATELIMIT_ENABLED = True
    LOGIN_RATE_LIMIT = '3 per minute'
    API_RATE_LIMIT = '500 per hour'
    
    # Production caching
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 600  # 10 minutes
    
    # Error handling
    PROPAGATE_EXCEPTIONS = False
    
    @staticmethod
    def init_app(app):
        """Production-specific initialization."""
        BaseConfig.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        formatter = logging.Formatter(BaseConfig.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

class DockerConfig(ProductionConfig):
    """Configuration for Docker deployments."""
    
    # Use environment variables for all configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    
    @classmethod
    def init_app(cls, app):
        """Docker-specific initialization."""
        ProductionConfig.init_app(app)
        
        # Log to stdout for container environments
        import logging
        from logging import StreamHandler
        import sys
        
        stream_handler = StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(cls.LOG_FORMAT)
        stream_handler.setFormatter(formatter)
        app.logger.addHandler(stream_handler)

class KubernetesConfig(DockerConfig):
    """Configuration for Kubernetes deployments."""
    
    @classmethod
    def init_app(cls, app):
        """Kubernetes-specific initialization."""
        DockerConfig.init_app(app)
        
        # Add structured logging for Kubernetes
        import json
        import logging
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                return json.dumps(log_entry)
        
        for handler in app.logger.handlers:
            handler.setFormatter(JSONFormatter())

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'kubernetes': KubernetesConfig,
    'default': DevelopmentConfig
} 