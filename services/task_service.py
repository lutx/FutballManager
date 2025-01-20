from typing import Dict, Optional, Any, List, Callable
from datetime import datetime, timedelta
import threading
import queue
import uuid
from flask import current_app

from models import SystemLog, Task
from services.base_service import BaseService
from services.notification_service import NotificationService

class TaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.notification_service = NotificationService()
        self._tasks = {}  # Słownik zadań {task_id: task_info}
        self._task_queue = queue.Queue()
        self._workers = []
        self._running = False
        self._max_workers = 3
        self._start_workers()

    def _start_workers(self) -> None:
        """Uruchamia wątki robocze"""
        self._running = True
        for _ in range(self._max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker_loop(self) -> None:
        """Główna pętla wątku roboczego"""
        while self._running:
            try:
                task = self._task_queue.get(timeout=1)
                if task:
                    self._execute_task(task)
                self._task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                current_app.logger.error(f'Worker error: {str(e)}')

    def _execute_task(self, task: Dict) -> None:
        """Wykonuje zadanie i aktualizuje jego status"""
        try:
            task_id = task['id']
            self._update_task_status(task_id, 'running')

            # Wykonaj zadanie
            result = task['function'](*task['args'], **task['kwargs'])
            
            # Aktualizuj status i wynik
            self._tasks[task_id]['result'] = result
            self._update_task_status(task_id, 'completed')
            
            # Powiadom o zakończeniu
            if task.get('notify_user'):
                self.notification_service.create_notification(
                    user_id=task['user_id'],
                    title="Zadanie zakończone",
                    message=f"Zadanie {task['name']} zostało zakończone pomyślnie",
                    notification_type='task_completed'
                )
        except Exception as e:
            error_msg = str(e)
            self._tasks[task_id]['error'] = error_msg
            self._update_task_status(task_id, 'failed')
            
            if task.get('notify_user'):
                self.notification_service.create_notification(
                    user_id=task['user_id'],
                    title="Błąd zadania",
                    message=f"Zadanie {task['name']} zakończyło się błędem: {error_msg}",
                    notification_type='task_failed'
                )

    def _update_task_status(self, task_id: str, status: str) -> None:
        """Aktualizuje status zadania"""
        try:
            if task_id in self._tasks:
                self._tasks[task_id]['status'] = status
                self._tasks[task_id]['updated_at'] = datetime.utcnow()

                # Zapisz do bazy danych
                task = Task.query.get(task_id)
                if task:
                    task.status = status
                    task.updated_at = datetime.utcnow()
                    if status == 'completed':
                        task.completed_at = datetime.utcnow()
                    if 'error' in self._tasks[task_id]:
                        task.error = self._tasks[task_id]['error']
                    self.commit()

        except Exception as e:
            current_app.logger.error(f'Error updating task status: {str(e)}')

    def submit_task(self, function: Callable, name: str, description: str = None,
                   args: tuple = None, kwargs: dict = None, user_id: Optional[int] = None,
                   notify_user: bool = True) -> str:
        """Dodaje nowe zadanie do kolejki"""
        try:
            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'name': name,
                'description': description,
                'function': function,
                'args': args or (),
                'kwargs': kwargs or {},
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'user_id': user_id,
                'notify_user': notify_user
            }
            
            # Zapisz do pamięci
            self._tasks[task_id] = task
            
            # Zapisz do bazy danych
            db_task = Task(
                id=task_id,
                name=name,
                description=description,
                status='pending',
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.add(db_task)
            self.commit()

            # Dodaj do kolejki
            self._task_queue.put(task)

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error submitting task: {str(e)}')
            raise

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania"""
        try:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                return {
                    'id': task_id,
                    'name': task['name'],
                    'status': task['status'],
                    'created_at': task['created_at'],
                    'updated_at': task['updated_at'],
                    'error': task.get('error'),
                    'result': task.get('result')
                }
            return None
        except Exception as e:
            current_app.logger.error(f'Error getting task status: {str(e)}')
            return None

    def get_user_tasks(self, user_id: int, status: Optional[str] = None,
                      limit: int = 50) -> List[Dict]:
        """Pobiera zadania użytkownika"""
        try:
            query = Task.query.filter_by(user_id=user_id)
            if status:
                query = query.filter_by(status=status)
            
            return [{
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'completed_at': task.completed_at,
                'error': task.error
            } for task in query.order_by(Task.created_at.desc()).limit(limit)]
        except Exception as e:
            current_app.logger.error(f'Error getting user tasks: {str(e)}')
            return []

    def cancel_task(self, task_id: str) -> bool:
        """Anuluje zadanie jeśli jeszcze nie zostało rozpoczęte"""
        try:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]
            if task['status'] == 'pending':
                self._update_task_status(task_id, 'cancelled')
                return True
            return False
        except Exception as e:
            current_app.logger.error(f'Error cancelling task: {str(e)}')
            return False

    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Usuwa stare zakończone zadania"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Usuń z bazy danych
            deleted = Task.query.filter(
                Task.updated_at < cutoff_date,
                Task.status.in_(['completed', 'failed', 'cancelled'])
            ).delete()

            # Usuń z pamięci
            current_time = datetime.utcnow()
            task_ids = [
                task_id for task_id, task in self._tasks.items()
                if task['updated_at'] < cutoff_date and
                task['status'] in ['completed', 'failed', 'cancelled']
            ]
            
            for task_id in task_ids:
                del self._tasks[task_id]

            self.commit()
            return deleted
        except Exception as e:
            current_app.logger.error(f'Error cleaning up tasks: {str(e)}')
            return 0

    def get_queue_stats(self) -> Dict:
        """Zwraca statystyki kolejki zadań"""
        try:
            total_tasks = len(self._tasks)
            pending = sum(1 for task in self._tasks.values() if task['status'] == 'pending')
            running = sum(1 for task in self._tasks.values() if task['status'] == 'running')
            completed = sum(1 for task in self._tasks.values() if task['status'] == 'completed')
            failed = sum(1 for task in self._tasks.values() if task['status'] == 'failed')
            cancelled = sum(1 for task in self._tasks.values() if task['status'] == 'cancelled')

            return {
                'total_tasks': total_tasks,
                'pending': pending,
                'running': running,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'queue_size': self._task_queue.qsize(),
                'active_workers': len(self._workers)
            }
        except Exception as e:
            current_app.logger.error(f'Error getting queue stats: {str(e)}')
            return {
                'total_tasks': 0,
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
                'queue_size': 0,
                'active_workers': 0
            } 