from typing import Optional, Dict, List
from datetime import datetime, timedelta
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.notification_service import NotificationService
from services.config_service import ConfigService

class NotificationTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.notification_service = NotificationService()
        self.config_service = ConfigService()

    def schedule_notification_cleanup(self, days: int = 30,
                                   user_id: Optional[int] = None) -> str:
        """Planuje zadanie czyszczenia starych powiadomień"""
        try:
            task_id = self.task_service.submit_task(
                function=self._cleanup_notifications,
                name='Czyszczenie powiadomień',
                description=f'Usuwanie powiadomień starszych niż {days} dni',
                args=(days,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling notification cleanup: {str(e)}')
            raise

    def _cleanup_notifications(self, days: int) -> Dict:
        """Czyści stare powiadomienia"""
        try:
            deleted_count = self.notification_service.clear_old_notifications(days)
            
            return {
                'deleted_notifications': deleted_count,
                'days': days,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error cleaning up notifications: {str(e)}')
            raise

    def schedule_match_notifications(self, match_id: int,
                                  user_id: Optional[int] = None) -> str:
        """Planuje zadanie wysyłania powiadomień o meczu"""
        try:
            task_id = self.task_service.submit_task(
                function=self._send_match_notifications,
                name=f'Powiadomienia o meczu {match_id}',
                description=f'Wysyłanie powiadomień o meczu {match_id}',
                args=(match_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling match notifications: {str(e)}')
            raise

    def _send_match_notifications(self, match_id: int) -> Dict:
        """Wysyła powiadomienia związane z meczem"""
        try:
            # Powiadomienie o rozpoczęciu
            start_notifications = self.notification_service.notify_match_start(match_id)
            
            # Powiadomienie o zakończeniu
            end_notifications = self.notification_service.notify_match_end(match_id)

            return {
                'match_id': match_id,
                'start_notifications': start_notifications,
                'end_notifications': end_notifications,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error sending match notifications: {str(e)}')
            raise

    def schedule_tournament_notifications(self, tournament_id: int,
                                       user_id: Optional[int] = None) -> str:
        """Planuje zadanie wysyłania powiadomień o turnieju"""
        try:
            task_id = self.task_service.submit_task(
                function=self._send_tournament_notifications,
                name=f'Powiadomienia o turnieju {tournament_id}',
                description=f'Wysyłanie powiadomień o turnieju {tournament_id}',
                args=(tournament_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling tournament notifications: {str(e)}')
            raise

    def _send_tournament_notifications(self, tournament_id: int) -> Dict:
        """Wysyła powiadomienia związane z turniejem"""
        try:
            # Powiadomienie o rozpoczęciu
            start_notifications = self.notification_service.notify_tournament_start(tournament_id)
            
            # Powiadomienie o zakończeniu
            end_notifications = self.notification_service.notify_tournament_end(tournament_id)

            return {
                'tournament_id': tournament_id,
                'start_notifications': start_notifications,
                'end_notifications': end_notifications,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error sending tournament notifications: {str(e)}')
            raise

    def schedule_bulk_notifications(self, notifications: List[Dict],
                                 user_id: Optional[int] = None) -> str:
        """Planuje zadanie wysyłania wielu powiadomień"""
        try:
            task_id = self.task_service.submit_task(
                function=self._send_bulk_notifications,
                name='Wysyłanie powiadomień grupowych',
                description=f'Wysyłanie {len(notifications)} powiadomień',
                args=(notifications,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling bulk notifications: {str(e)}')
            raise

    def _send_bulk_notifications(self, notifications: List[Dict]) -> Dict:
        """Wysyła wiele powiadomień"""
        try:
            results = []
            for notification in notifications:
                try:
                    notification_id = self.notification_service.create_notification(
                        user_id=notification.get('user_id'),
                        title=notification.get('title'),
                        message=notification.get('message'),
                        notification_type=notification.get('type', 'info')
                    )
                    results.append({
                        'status': 'success',
                        'notification_id': notification_id
                    })
                except Exception as e:
                    results.append({
                        'status': 'error',
                        'error': str(e)
                    })

            return {
                'total': len(notifications),
                'successful': len([r for r in results if r['status'] == 'success']),
                'failed': len([r for r in results if r['status'] == 'error']),
                'results': results,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error sending bulk notifications: {str(e)}')
            raise

    def get_notification_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania powiadomień"""
        return self.task_service.get_task_status(task_id)

    def cancel_notification_task(self, task_id: str) -> bool:
        """Anuluje zadanie powiadomień"""
        return self.task_service.cancel_task(task_id)

    def get_user_notification_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań powiadomień użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 