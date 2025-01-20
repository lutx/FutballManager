import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import current_app
from models import SystemLog, db
from services.logging_service import LoggingService

class MonitoringService:
    @staticmethod
    def get_system_metrics() -> Dict:
        """Pobiera podstawowe metryki systemowe."""
        try:
            metrics = {
                'cpu': {
                    'percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent
                },
                'timestamp': datetime.utcnow()
            }
            return metrics
        except Exception as e:
            current_app.logger.error(f'Błąd podczas pobierania metryk systemowych: {str(e)}')
            raise

    @staticmethod
    def get_application_metrics() -> Dict:
        """Pobiera metryki związane z aplikacją."""
        try:
            process = psutil.Process(os.getpid())
            metrics = {
                'process': {
                    'cpu_percent': process.cpu_percent(interval=1),
                    'memory_percent': process.memory_percent(),
                    'memory_info': process.memory_info()._asdict(),
                    'threads': process.num_threads(),
                    'open_files': len(process.open_files()),
                    'connections': len(process.connections())
                },
                'database': {
                    'total_logs': SystemLog.query.count(),
                    'recent_logs': SystemLog.query.filter(
                        SystemLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
                    ).count()
                },
                'timestamp': datetime.utcnow()
            }
            return metrics
        except Exception as e:
            current_app.logger.error(f'Błąd podczas pobierania metryk aplikacji: {str(e)}')
            raise

    @staticmethod
    def monitor_database_performance() -> Dict:
        """Monitoruje wydajność bazy danych."""
        try:
            start_time = datetime.utcnow()
            # Wykonaj przykładowe zapytanie do bazy
            SystemLog.query.count()
            query_time = (datetime.utcnow() - start_time).total_seconds()

            metrics = {
                'query_time': query_time,
                'timestamp': datetime.utcnow()
            }
            return metrics
        except Exception as e:
            current_app.logger.error(f'Błąd podczas monitorowania wydajności bazy danych: {str(e)}')
            raise

    @staticmethod
    def check_system_health() -> Dict:
        """Sprawdza ogólny stan systemu."""
        try:
            system_metrics = MonitoringService.get_system_metrics()
            app_metrics = MonitoringService.get_application_metrics()
            db_metrics = MonitoringService.monitor_database_performance()

            # Definiuj progi ostrzeżeń
            warnings = []
            if system_metrics['cpu']['percent'] > 80:
                warnings.append('Wysokie użycie CPU')
            if system_metrics['memory']['percent'] > 80:
                warnings.append('Wysokie użycie pamięci')
            if system_metrics['disk']['percent'] > 80:
                warnings.append('Mało miejsca na dysku')
            if db_metrics['query_time'] > 1.0:
                warnings.append('Wolne zapytania do bazy danych')

            health_status = {
                'status': 'warning' if warnings else 'healthy',
                'warnings': warnings,
                'metrics': {
                    'system': system_metrics,
                    'application': app_metrics,
                    'database': db_metrics
                },
                'timestamp': datetime.utcnow()
            }

            # Loguj ostrzeżenia
            if warnings:
                LoggingService.add_log(
                    type='warning',
                    user='system',
                    action='health_check',
                    details=str(warnings)
                )

            return health_status
        except Exception as e:
            current_app.logger.error(f'Błąd podczas sprawdzania stanu systemu: {str(e)}')
            raise

    @staticmethod
    def get_performance_history(hours: int = 24) -> List[Dict]:
        """Pobiera historię wydajności systemu."""
        try:
            start_date = datetime.utcnow() - timedelta(hours=hours)
            logs = SystemLog.query.filter(
                SystemLog.timestamp >= start_date,
                SystemLog.action == 'health_check'
            ).order_by(SystemLog.timestamp.asc()).all()

            history = []
            for log in logs:
                history.append({
                    'timestamp': log.timestamp,
                    'status': 'warning' if log.details else 'healthy',
                    'warnings': eval(log.details) if log.details else []
                })

            return history
        except Exception as e:
            current_app.logger.error(f'Błąd podczas pobierania historii wydajności: {str(e)}')
            raise 