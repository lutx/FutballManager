from typing import Optional, Dict
from datetime import datetime, timedelta
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.log_service import LogService
from services.notification_service import NotificationService
from services.cache_service import CacheService
from services.config_service import ConfigService

class MaintenanceTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.log_service = LogService()
        self.notification_service = NotificationService()
        self.cache_service = CacheService()
        self.config_service = ConfigService()

    def schedule_log_cleanup(self, days: int = 30,
                           user_id: Optional[int] = None) -> str:
        """Planuje zadanie czyszczenia starych logów"""
        try:
            task_id = self.task_service.submit_task(
                function=self._cleanup_logs,
                name='Czyszczenie logów systemowych',
                description=f'Usuwanie logów starszych niż {days} dni',
                args=(days,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling log cleanup: {str(e)}')
            raise

    def _cleanup_logs(self, days: int) -> Dict:
        """Czyści stare logi systemowe"""
        try:
            deleted_count = self.log_service.clear_old_logs(days)
            
            return {
                'deleted_logs': deleted_count,
                'days': days,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error cleaning up logs: {str(e)}')
            raise

    def schedule_cache_cleanup(self, user_id: Optional[int] = None) -> str:
        """Planuje zadanie czyszczenia cache'u"""
        try:
            task_id = self.task_service.submit_task(
                function=self._cleanup_cache,
                name='Czyszczenie cache systemu',
                description='Usuwanie wygasłych wpisów z cache',
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling cache cleanup: {str(e)}')
            raise

    def _cleanup_cache(self) -> Dict:
        """Czyści wygasłe wpisy z cache'u"""
        try:
            # Pobierz statystyki przed czyszczeniem
            before_stats = self.cache_service.get_stats()
            
            # Wykonaj czyszczenie
            deleted_count = self.cache_service.cleanup_expired()
            
            # Pobierz statystyki po czyszczeniu
            after_stats = self.cache_service.get_stats()

            return {
                'deleted_entries': deleted_count,
                'before_stats': before_stats,
                'after_stats': after_stats,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error cleaning up cache: {str(e)}')
            raise

    def schedule_task_cleanup(self, days: int = 30,
                            user_id: Optional[int] = None) -> str:
        """Planuje zadanie czyszczenia starych zadań"""
        try:
            task_id = self.task_service.submit_task(
                function=self._cleanup_tasks,
                name='Czyszczenie starych zadań',
                description=f'Usuwanie zakończonych zadań starszych niż {days} dni',
                args=(days,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling task cleanup: {str(e)}')
            raise

    def _cleanup_tasks(self, days: int) -> Dict:
        """Czyści stare zakończone zadania"""
        try:
            deleted_count = self.task_service.cleanup_old_tasks(days)
            
            return {
                'deleted_tasks': deleted_count,
                'days': days,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error cleaning up tasks: {str(e)}')
            raise

    def schedule_system_health_check(self, user_id: Optional[int] = None) -> str:
        """Planuje zadanie sprawdzenia stanu systemu"""
        try:
            task_id = self.task_service.submit_task(
                function=self._check_system_health,
                name='Sprawdzenie stanu systemu',
                description='Kompleksowe sprawdzenie stanu systemu',
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling health check: {str(e)}')
            raise

    def _check_system_health(self) -> Dict:
        """Sprawdza stan systemu"""
        try:
            # Sprawdź stan cache'u
            cache_stats = self.cache_service.get_stats()
            
            # Sprawdź kolejkę zadań
            task_stats = self.task_service.get_queue_stats()
            
            # Sprawdź konfigurację
            config = self.config_service.get_config()
            config_validation = self.config_service.validate_config()
            
            # Sprawdź użycie pamięci i inne metryki
            system_metrics = self._get_system_metrics()

            return {
                'cache_health': cache_stats,
                'task_queue_health': task_stats,
                'config_health': {
                    'config': config,
                    'validation_errors': config_validation
                },
                'system_metrics': system_metrics,
                'checked_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error checking system health: {str(e)}')
            raise

    def _get_system_metrics(self) -> Dict:
        """Pobiera metryki systemowe"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            return {
                'memory_usage': process.memory_info().rss,
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
        except ImportError:
            current_app.logger.warning('psutil not available, skipping detailed metrics')
            return {}
        except Exception as e:
            current_app.logger.error(f'Error getting system metrics: {str(e)}')
            return {}

    def get_maintenance_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania utrzymania"""
        return self.task_service.get_task_status(task_id)

    def cancel_maintenance_task(self, task_id: str) -> bool:
        """Anuluje zadanie utrzymania"""
        return self.task_service.cancel_task(task_id)

    def get_user_maintenance_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań utrzymania użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 