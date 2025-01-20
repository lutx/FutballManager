import os
from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from extensions import db, bcrypt, login_manager, migrate, limiter
from models import User
from services.logging_service import LoggingService
from services.monitoring_service import MonitoringService
from tasks.monitoring_task import start_monitoring, stop_monitoring
from config import config
import logging
from logging.handlers import RotatingFileHandler
from views import init_views
import sys

def create_app(config_name='default'):
    """Tworzenie i konfiguracja aplikacji Flask."""
    try:
        app = Flask(__name__)
        
        # Konfiguracja z pliku config.py
        if config_name not in config:
            print(f"Error: Configuration '{config_name}' not found. Using 'default'")
            config_name = 'default'
        
        app.config.from_object(config[config_name])
        
        # Upewnij się, że wymagane katalogi istnieją
        os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Inicjalizacja rozszerzeń
        try:
            db.init_app(app)
            bcrypt.init_app(app)
            login_manager.init_app(app)
            migrate.init_app(app, db)
            limiter.init_app(app)
            csrf = CSRFProtect()
            csrf.init_app(app)
        except Exception as e:
            print(f"Failed to initialize extensions: {str(e)}")
            raise
        
        # Konfiguracja logowania
        LoggingService.setup_logging(app)
        
        # Konfiguracja Flask-Login
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'
        login_manager.login_message_category = 'info'
        
        @login_manager.user_loader
        def load_user(user_id):
            try:
                return User.query.get(int(user_id))
            except Exception as e:
                app.logger.error(f'Błąd podczas ładowania użytkownika: {str(e)}')
                return None
        
        # Inicjalizacja widoków i blueprintów
        try:
            init_views(app)
        except Exception as e:
            print(f"Failed to initialize views: {str(e)}")
            raise
        
        # Inicjalizacja bazy danych
        with app.app_context():
            try:
                db.create_all()
                app.logger.info('Baza danych została zainicjalizowana')
            except Exception as e:
                app.logger.error(f'Błąd podczas inicjalizacji bazy danych: {str(e)}')
                raise
        
        # Obsługa błędów
        @app.errorhandler(404)
        def not_found_error(error):
            app.logger.error(f'Nie znaleziono strony: {request.url}')
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            app.logger.error(f'Błąd serwera: {str(error)}')
            db.session.rollback()
            return render_template('errors/500.html'), 500

        @app.errorhandler(Exception)
        def handle_exception(error):
            app.logger.error(f'Nieobsłużony wyjątek: {str(error)}')
            db.session.rollback()
            return render_template('errors/500.html'), 500
        
        # Start monitorowania w trybie produkcyjnym
        if not app.debug and not hasattr(app, 'monitoring_thread'):
            try:
                app.monitoring_thread = start_monitoring(app)
                
                @app.before_first_request
                def init_app():
                    LoggingService.add_log(
                        type='info',
                        user='system',
                        action='app_start',
                        details='Aplikacja została uruchomiona'
                    )
                
                @app.teardown_appcontext
                def cleanup(error):
                    if error:
                        app.logger.error(f'Błąd podczas zamykania kontekstu: {str(error)}')
                    if hasattr(app, 'monitoring_thread'):
                        stop_monitoring(app.monitoring_thread)
            except Exception as e:
                app.logger.error(f'Błąd podczas uruchamiania monitorowania: {str(e)}')
        
        return app
        
    except Exception as e:
        print(f"Failed to create application: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        app = create_app()
        
        # Próba inicjalizacji admina tylko w trybie debug
        if app.debug:
            try:
                from init_admin import init_admin
                with app.app_context():
                    init_admin(app)
            except Exception as e:
                print(f"Warning: Could not initialize admin: {str(e)}")
        
        # Uruchom aplikację
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=app.debug)
        
    except Exception as e:
        print(f"Critical error during application startup: {str(e)}")
        logging.error(f"Critical error during application startup: {str(e)}")
        sys.exit(1)
