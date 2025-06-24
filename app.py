import os
import logging
import sys
from datetime import timedelta
from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from flask_caching import Cache
from flask_cors import CORS
from extensions import db, bcrypt, login_manager, migrate, limiter
from models import User
from services.logging_service import LoggingService
from services.monitoring_service import MonitoringService
from tasks.monitoring_task import start_monitoring, stop_monitoring
from config import config
from views import init_views

# Initialize modern extensions
socketio = SocketIO()
cache = Cache()

def create_app(config_name='default'):
    """Create and configure Flask application with modern 2025 patterns."""
    try:
        app = Flask(__name__)
        
        # Configuration
        if config_name not in config:
            print(f"Error: Configuration '{config_name}' not found. Using 'default'")
            config_name = 'default'
        
        app.config.from_object(config[config_name])
        
        # Modern Flask 3.x security configurations
        app.config.update(
            # Enhanced security
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
            
            # Modern caching
            CACHE_TYPE='redis' if os.environ.get('REDIS_URL') else 'simple',
            CACHE_DEFAULT_TIMEOUT=300,
            
            # WebSocket configuration
            SECRET_KEY=app.config.get('SECRET_KEY'),
            
            # Performance settings
            SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 1 year for static files
        )
        
        # Ensure required directories exist
        os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Initialize extensions with modern patterns
        try:
            # Core extensions
            db.init_app(app)
            bcrypt.init_app(app)
            login_manager.init_app(app)
            migrate.init_app(app, db)
            limiter.init_app(app)
            
            # Modern extensions
            csrf = CSRFProtect()
            csrf.init_app(app)
            socketio.init_app(app, cors_allowed_origins="*", 
                            async_mode='eventlet', 
                            logger=True, 
                            engineio_logger=True)
            cache.init_app(app)
            
            # Enable CORS for API endpoints
            CORS(app, resources={
                r"/api/*": {"origins": "*"},
                r"/socket.io/*": {"origins": "*"}
            })
            
        except Exception as e:
            print(f"Failed to initialize extensions: {str(e)}")
            raise
        
        # Enhanced logging setup
        LoggingService.setup_logging(app)
        
        # Modern Flask-Login configuration
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        login_manager.session_protection = 'strong'
        
        @login_manager.user_loader
        def load_user(user_id):
            try:
                return User.query.get(int(user_id))
            except Exception as e:
                app.logger.error(f'Error loading user: {str(e)}')
                return None
        
        # Initialize views and blueprints
        try:
            init_views(app)
            init_socketio_events(app)
        except Exception as e:
            print(f"Failed to initialize views: {str(e)}")
            raise
        
        # Database initialization with modern patterns
        with app.app_context():
            try:
                db.create_all()
                app.logger.info('Database initialized successfully')
            except Exception as e:
                app.logger.error(f'Database initialization error: {str(e)}')
                raise
        
        # Modern error handlers with better UX
        @app.errorhandler(404)
        def not_found_error(error):
            app.logger.error(f'Page not found: {request.url}')
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            app.logger.error(f'Server error: {str(error)}')
            db.session.rollback()
            return render_template('errors/500.html'), 500

        @app.errorhandler(403)
        def forbidden_error(error):
            app.logger.warning(f'Forbidden access attempt: {request.url}')
            return render_template('errors/403.html'), 403

        @app.errorhandler(429)
        def ratelimit_handler(e):
            app.logger.warning(f'Rate limit exceeded: {request.remote_addr}')
            return render_template('errors/429.html'), 429

        @app.errorhandler(Exception)
        def handle_exception(error):
            app.logger.error(f'Unhandled exception: {str(error)}', exc_info=True)
            db.session.rollback()
            return render_template('errors/500.html'), 500
        
        # Modern security headers
        @app.after_request
        def after_request(response):
            # Security headers for 2025 standards
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
                "font-src 'self' fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self' ws: wss:;"
            )
            return response
        
        # Health check endpoint for modern deployment
        @app.route('/health')
        def health_check():
            return {'status': 'healthy', 'version': '2025.1'}, 200
        
        # Start monitoring in production
        if not app.debug and not app.testing:
            try:
                app.monitoring_thread = start_monitoring(app)
                
                # Modern application lifecycle hooks
                @app.before_request
                def before_request():
                    # Log request for monitoring
                    if not request.endpoint or request.endpoint != 'health_check':
                        app.logger.debug(f'Request: {request.method} {request.path}')
                
                @app.teardown_appcontext
                def cleanup(error):
                    if error:
                        app.logger.error(f'Context cleanup error: {str(error)}')
                    if hasattr(app, 'monitoring_thread'):
                        stop_monitoring(app.monitoring_thread)
            except Exception as e:
                app.logger.error(f'Monitoring startup error: {str(e)}')
        
        return app
        
    except Exception as e:
        print(f"Failed to create application: {str(e)}")
        logging.error(f"Critical application creation error: {str(e)}")
        raise

def init_socketio_events(app):
    """Initialize WebSocket events for real-time features."""
    
    @socketio.on('connect')
    def handle_connect():
        app.logger.info(f'Client connected: {request.sid}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        app.logger.info(f'Client disconnected: {request.sid}')
    
    @socketio.on('join_match')
    def handle_join_match(data):
        """Join a match room for real-time updates."""
        match_id = data.get('match_id')
        if match_id:
            from flask_socketio import join_room
            join_room(f'match_{match_id}')
            app.logger.info(f'Client {request.sid} joined match {match_id}')

if __name__ == '__main__':
    try:
        app = create_app()
        
        # Initialize admin only in debug mode
        if app.debug:
            try:
                from init_admin import init_admin
                with app.app_context():
                    init_admin(app)
            except Exception as e:
                print(f"Warning: Could not initialize admin: {str(e)}")
        
        # Modern development server configuration
        port = int(os.environ.get('PORT', 5000))
        debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        
        # Use SocketIO for development with WebSocket support
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=port, 
            debug=debug_mode,
            use_reloader=debug_mode,
            log_output=debug_mode
        )
        
    except Exception as e:
        print(f"Critical error during application startup: {str(e)}")
        logging.error(f"Critical startup error: {str(e)}")
        sys.exit(1)
