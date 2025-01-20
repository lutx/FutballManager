from datetime import datetime
from services.monitoring_service import MonitoringService
from services.logging_service import LoggingService
from flask import current_app
import schedule
import time
import threading

def monitor_system():
    """Funkcja monitorująca system."""
    try:
        # Sprawdź stan systemu
        health_status = MonitoringService.check_system_health()
        
        # Loguj wyniki
        if health_status['status'] == 'warning':
            LoggingService.add_log(
                type='warning',
                user='system',
                action='system_monitoring',
                details=str(health_status['warnings'])
            )
        else:
            LoggingService.add_log(
                type='info',
                user='system',
                action='system_monitoring',
                details='System działa prawidłowo'
            )

        # Wyczyść stare logi co 24 godziny
        if datetime.utcnow().hour == 0:
            LoggingService.clear_old_logs(days=30)

    except Exception as e:
        current_app.logger.error(f'Błąd podczas monitorowania systemu: {str(e)}')
        LoggingService.add_log(
            type='error',
            user='system',
            action='system_monitoring',
            details=str(e)
        )

def start_monitoring(app):
    """Uruchamia zadanie monitorowania w osobnym wątku."""
    def run_monitoring():
        with app.app_context():
            while True:
                monitor_system()
                time.sleep(300)  # Sprawdzaj co 5 minut

    monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
    monitoring_thread.start()

    current_app.logger.info('Uruchomiono monitoring systemu')
    return monitoring_thread

def stop_monitoring(monitoring_thread):
    """Zatrzymuje monitoring systemu."""
    if monitoring_thread and monitoring_thread.is_alive():
        monitoring_thread.join(timeout=1)
        current_app.logger.info('Zatrzymano monitoring systemu') 