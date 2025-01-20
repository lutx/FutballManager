from typing import Optional, Dict, List
from datetime import datetime, timedelta
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.notification_service import NotificationService
from services.stats_service import StatsService
from services.config_service import ConfigService
from models.tournament_standing import TournamentStanding
from models import TeamStats, Team
from extensions.database import db

class SyncTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.notification_service = NotificationService()
        self.stats_service = StatsService()
        self.config_service = ConfigService()

    def schedule_tournament_sync(self, tournament_id: int,
                               user_id: Optional[int] = None) -> str:
        """Planuje zadanie synchronizacji danych turnieju"""
        try:
            task_id = self.task_service.submit_task(
                function=self._sync_tournament_data,
                name=f'Synchronizacja turnieju {tournament_id}',
                description=f'Synchronizacja i aktualizacja danych turnieju {tournament_id}',
                args=(tournament_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling tournament sync: {str(e)}')
            raise

    def _sync_tournament_data(self, tournament_id: int) -> Dict:
        """Synchronizuje dane turnieju"""
        try:
            # Aktualizacja statystyk turnieju
            tournament_stats = self.stats_service.get_tournament_stats(tournament_id)
            
            # Aktualizacja statystyk drużyn
            team_stats = []
            for team in tournament_stats['teams']:
                team_history = self.stats_service.get_team_history(team['id'])
                team_stats.append({
                    'team': team,
                    'history': team_history
                })

            # Aktualizacja tabeli wyników
            standings = self._update_tournament_standings(tournament_id, team_stats)
            
            return {
                'tournament_id': tournament_id,
                'stats_updated': True,
                'standings_updated': standings,
                'team_stats': len(team_stats),
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error syncing tournament data: {str(e)}')
            raise

    def _update_tournament_standings(self, tournament_id: int,
                                   team_stats: List[Dict]) -> bool:
        """Aktualizuje tabelę wyników turnieju"""
        try:
            # Oblicz punkty i statystyki dla każdej drużyny
            standings = []
            for team in team_stats:
                history = team['history']
                stats = history.get('stats', {})
                
                standings.append({
                    'team_id': team['team']['id'],
                    'team_name': team['team']['name'],
                    'matches_played': stats.get('matches_played', 0),
                    'wins': stats.get('wins', 0),
                    'draws': stats.get('draws', 0),
                    'losses': stats.get('losses', 0),
                    'goals_for': stats.get('goals_scored', 0),
                    'goals_against': stats.get('goals_conceded', 0),
                    'points': (stats.get('wins', 0) * 3) + stats.get('draws', 0)
                })

            # Sortuj według punktów i różnicy bramek
            standings.sort(key=lambda x: (-x['points'],
                                      -(x['goals_for'] - x['goals_against']),
                                      -x['goals_for']))

            # Usuń stare wyniki
            TournamentStanding.query.filter_by(tournament_id=tournament_id).delete()

            # Zapisz nowe wyniki
            for position, standing in enumerate(standings, 1):
                new_standing = TournamentStanding(
                    tournament_id=tournament_id,
                    team_id=standing['team_id'],
                    matches_played=standing['matches_played'],
                    wins=standing['wins'],
                    draws=standing['draws'],
                    losses=standing['losses'],
                    goals_for=standing['goals_for'],
                    goals_against=standing['goals_against'],
                    points=standing['points'],
                    position=position
                )
                db.session.add(new_standing)

            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error updating tournament standings: {str(e)}')
            db.session.rollback()
            return False

    def schedule_team_stats_sync(self, team_id: int,
                               user_id: Optional[int] = None) -> str:
        """Planuje zadanie synchronizacji statystyk drużyny"""
        try:
            task_id = self.task_service.submit_task(
                function=self._sync_team_stats,
                name=f'Synchronizacja statystyk drużyny {team_id}',
                description=f'Synchronizacja i aktualizacja statystyk drużyny {team_id}',
                args=(team_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling team stats sync: {str(e)}')
            raise

    def _sync_team_stats(self, team_id: int) -> Dict:
        """Synchronizuje statystyki drużyny"""
        try:
            # Pobierz drużynę i jej turniej
            team = Team.query.get(team_id)
            if not team:
                raise ValueError(f'Nie znaleziono drużyny o ID {team_id}')

            # Pobierz i zaktualizuj historię drużyny
            team_history = self.stats_service.get_team_history(team_id)
            stats = team_history.get('stats', {})
            
            # Oblicz dodatkowe statystyki
            advanced_stats = self._calculate_advanced_stats(team_history)
            
            # Znajdź lub utwórz obiekt statystyk
            team_stats = TeamStats.query.filter_by(
                team_id=team_id,
                tournament_id=team.tournament_id
            ).first()
            
            if not team_stats:
                team_stats = TeamStats(
                    team_id=team_id,
                    tournament_id=team.tournament_id
                )
                db.session.add(team_stats)
            
            # Aktualizuj podstawowe statystyki
            team_stats.matches_played = stats.get('matches_played', 0)
            team_stats.wins = stats.get('wins', 0)
            team_stats.draws = stats.get('draws', 0)
            team_stats.losses = stats.get('losses', 0)
            team_stats.goals_scored = stats.get('goals_scored', 0)
            team_stats.goals_conceded = stats.get('goals_conceded', 0)
            
            # Aktualizuj zaawansowane statystyki
            if advanced_stats:
                team_stats.shots_on_target = advanced_stats.get('shots_on_target', 0)
                team_stats.shots_off_target = advanced_stats.get('shots_off_target', 0)
                team_stats.possession = advanced_stats.get('possession', 0.0)
            
            db.session.commit()
            
            return {
                'team_id': team_id,
                'basic_stats_updated': True,
                'advanced_stats_updated': advanced_stats is not None,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error syncing team stats: {str(e)}')
            db.session.rollback()
            raise

    def _calculate_advanced_stats(self, team_history: Dict) -> Optional[Dict]:
        """Oblicza zaawansowane statystyki drużyny"""
        try:
            matches = team_history.get('matches', [])
            if not matches:
                return None

            # Analiza formy
            recent_form = []
            for match in matches[-5:]:  # Ostatnie 5 meczów
                if match['result'] == 'win':
                    recent_form.append('W')
                elif match['result'] == 'loss':
                    recent_form.append('L')
                else:
                    recent_form.append('D')

            # Oblicz średnie i trendy
            goals_scored = [m['team_score'] for m in matches if 'team_score' in m]
            goals_conceded = [m['opponent_score'] for m in matches if 'opponent_score' in m]

            return {
                'recent_form': ''.join(recent_form),
                'avg_goals_scored': sum(goals_scored) / len(goals_scored) if goals_scored else 0,
                'avg_goals_conceded': sum(goals_conceded) / len(goals_conceded) if goals_conceded else 0,
                'clean_sheets': sum(1 for m in matches if m.get('opponent_score', 0) == 0),
                'matches_analyzed': len(matches)
            }
        except Exception as e:
            current_app.logger.error(f'Error calculating advanced stats: {str(e)}')
            return None

    def schedule_global_stats_sync(self, user_id: Optional[int] = None) -> str:
        """Planuje zadanie synchronizacji globalnych statystyk"""
        try:
            task_id = self.task_service.submit_task(
                function=self._sync_global_stats,
                name='Synchronizacja globalnych statystyk',
                description='Synchronizacja i aktualizacja globalnych statystyk systemu',
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error scheduling global stats sync: {str(e)}')
            raise

    def _sync_global_stats(self) -> Dict:
        """Synchronizuje globalne statystyki"""
        try:
            # Pobierz aktualne statystyki
            global_stats = self.stats_service.get_global_stats()
            
            # TODO: Zapisz zaktualizowane statystyki do bazy danych
            
            return {
                'stats_updated': True,
                'stats': global_stats,
                'executed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error syncing global stats: {str(e)}')
            raise

    def get_sync_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania synchronizacji"""
        return self.task_service.get_task_status(task_id)

    def cancel_sync_task(self, task_id: str) -> bool:
        """Anuluje zadanie synchronizacji"""
        return self.task_service.cancel_task(task_id)

    def get_user_sync_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań synchronizacji użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 