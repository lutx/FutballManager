from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json
import os
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.notification_service import NotificationService
from services.stats_service import StatsService
from services.config_service import ConfigService

class ArchiveTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.notification_service = NotificationService()
        self.stats_service = StatsService()
        self.config_service = ConfigService()

    def schedule_tournament_archive(self, tournament_id: int,
                                  user_id: Optional[int] = None) -> str:
        """Planuje zadanie archiwizacji turnieju"""
        try:
            task_id = self.task_service.submit_task(
                function=self._archive_tournament,
                name=f'Archiwizacja turnieju {tournament_id}',
                description=f'Archiwizacja danych turnieju {tournament_id}',
                args=(tournament_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling tournament archive: {str(e)}')
            raise

    def _archive_tournament(self, tournament_id: int) -> Dict:
        """Archiwizuje dane turnieju"""
        try:
            # Pobierz dane turnieju
            tournament_data = self.stats_service.get_tournament_stats(tournament_id)
            
            # Pobierz dane drużyn
            team_data = []
            for team in tournament_data['teams']:
                team_history = self.stats_service.get_team_history(team['id'])
                team_data.append({
                    'team': team,
                    'history': team_history
                })

            # Przygotuj dane do archiwizacji
            archive_data = {
                'tournament': tournament_data,
                'teams': team_data,
                'archived_at': datetime.utcnow().isoformat()
            }

            # Zapisz archiwum
            archive_path = self._save_archive(
                f'tournament_{tournament_id}',
                archive_data
            )

            return {
                'tournament_id': tournament_id,
                'archive_path': archive_path,
                'data_size': len(json.dumps(archive_data)),
                'teams_archived': len(team_data),
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error archiving tournament: {str(e)}')
            raise

    def schedule_team_archive(self, team_id: int,
                            user_id: Optional[int] = None) -> str:
        """Planuje zadanie archiwizacji drużyny"""
        try:
            task_id = self.task_service.submit_task(
                function=self._archive_team,
                name=f'Archiwizacja drużyny {team_id}',
                description=f'Archiwizacja danych drużyny {team_id}',
                args=(team_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling team archive: {str(e)}')
            raise

    def _archive_team(self, team_id: int) -> Dict:
        """Archiwizuje dane drużyny"""
        try:
            # Pobierz historię drużyny
            team_history = self.stats_service.get_team_history(team_id)
            
            # Przygotuj dane do archiwizacji
            archive_data = {
                'team': team_history['team'],
                'history': team_history,
                'archived_at': datetime.utcnow().isoformat()
            }

            # Zapisz archiwum
            archive_path = self._save_archive(
                f'team_{team_id}',
                archive_data
            )

            return {
                'team_id': team_id,
                'archive_path': archive_path,
                'data_size': len(json.dumps(archive_data)),
                'matches_archived': len(team_history.get('matches', [])),
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error archiving team: {str(e)}')
            raise

    def schedule_season_archive(self, season_year: int,
                              user_id: Optional[int] = None) -> str:
        """Planuje zadanie archiwizacji sezonu"""
        try:
            task_id = self.task_service.submit_task(
                function=self._archive_season,
                name=f'Archiwizacja sezonu {season_year}',
                description=f'Archiwizacja danych z sezonu {season_year}',
                args=(season_year,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling season archive: {str(e)}')
            raise

    def _archive_season(self, season_year: int) -> Dict:
        """Archiwizuje dane z całego sezonu"""
        try:
            # TODO: Pobierz wszystkie turnieje z danego sezonu
            tournaments = []  # Implementacja pobierania turniejów
            
            # Archiwizuj każdy turniej
            archived_tournaments = []
            for tournament in tournaments:
                try:
                    archive_data = self._archive_tournament(tournament['id'])
                    archived_tournaments.append({
                        'tournament_id': tournament['id'],
                        'status': 'success',
                        'archive_data': archive_data
                    })
                except Exception as e:
                    archived_tournaments.append({
                        'tournament_id': tournament['id'],
                        'status': 'error',
                        'error': str(e)
                    })

            # Przygotuj podsumowanie sezonu
            season_summary = {
                'year': season_year,
                'tournaments': archived_tournaments,
                'archived_at': datetime.utcnow().isoformat()
            }

            # Zapisz podsumowanie sezonu
            summary_path = self._save_archive(
                f'season_{season_year}_summary',
                season_summary
            )

            return {
                'season_year': season_year,
                'summary_path': summary_path,
                'total_tournaments': len(tournaments),
                'successful_archives': len([t for t in archived_tournaments 
                                         if t['status'] == 'success']),
                'failed_archives': len([t for t in archived_tournaments 
                                      if t['status'] == 'error']),
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error archiving season: {str(e)}')
            raise

    def _save_archive(self, name: str, data: Dict) -> str:
        """Zapisuje dane archiwum do pliku"""
        try:
            # Utwórz katalog archiwum jeśli nie istnieje
            archive_dir = os.path.join(current_app.instance_path, 'archives')
            os.makedirs(archive_dir, exist_ok=True)

            # Utwórz nazwę pliku z datą
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f'{name}_{timestamp}.json'
            filepath = os.path.join(archive_dir, filename)

            # Zapisz dane do pliku
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return filepath
        except Exception as e:
            current_app.logger.error(f'Error saving archive: {str(e)}')
            raise

    def get_archive_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania archiwizacji"""
        return self.task_service.get_task_status(task_id)

    def cancel_archive_task(self, task_id: str) -> bool:
        """Anuluje zadanie archiwizacji"""
        return self.task_service.cancel_task(task_id)

    def get_user_archive_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań archiwizacji użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 