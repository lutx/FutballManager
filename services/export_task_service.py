from typing import Optional, Dict
from datetime import datetime
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.export_service import ExportService
from services.notification_service import NotificationService

class ExportTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.export_service = ExportService()
        self.notification_service = NotificationService()

    def export_tournament_data(self, tournament_id: int, format: str,
                             user_id: Optional[int] = None) -> str:
        """Rozpoczyna zadanie eksportu danych turnieju"""
        try:
            # Wybierz odpowiednią funkcję eksportu
            export_func = None
            if format == 'csv':
                export_func = self.export_service.export_tournament_to_csv
            elif format == 'json':
                export_func = self.export_service.export_tournament_to_json
            elif format == 'excel':
                export_func = self.export_service.export_tournament_to_excel
            else:
                raise ValueError(f'Nieobsługiwany format eksportu: {format}')

            # Utwórz i uruchom zadanie
            task_id = self.task_service.submit_task(
                function=export_func,
                name=f'Export turnieju {tournament_id} do {format}',
                description=f'Eksport danych turnieju {tournament_id} do formatu {format}',
                args=(tournament_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error starting tournament export task: {str(e)}')
            raise

    def export_team_history(self, team_id: int, format: str,
                          user_id: Optional[int] = None) -> str:
        """Rozpoczyna zadanie eksportu historii drużyny"""
        try:
            # Wybierz odpowiednią funkcję eksportu
            if format not in ['csv', 'json']:
                raise ValueError(f'Nieobsługiwany format eksportu: {format}')

            task_id = self.task_service.submit_task(
                function=self.export_service.export_team_history,
                name=f'Export historii drużyny {team_id}',
                description=f'Eksport historii drużyny {team_id} do formatu {format}',
                args=(team_id, format),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error starting team history export task: {str(e)}')
            raise

    def export_global_stats(self, format: str, user_id: Optional[int] = None) -> str:
        """Rozpoczyna zadanie eksportu globalnych statystyk"""
        try:
            if format not in ['csv', 'json']:
                raise ValueError(f'Nieobsługiwany format eksportu: {format}')

            task_id = self.task_service.submit_task(
                function=self.export_service.export_global_stats,
                name=f'Export globalnych statystyk',
                description=f'Eksport globalnych statystyk systemu do formatu {format}',
                args=(format,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error starting global stats export task: {str(e)}')
            raise

    def get_export_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania eksportu"""
        return self.task_service.get_task_status(task_id)

    def cancel_export_task(self, task_id: str) -> bool:
        """Anuluje zadanie eksportu"""
        return self.task_service.cancel_task(task_id)

    def get_user_export_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań eksportu użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 