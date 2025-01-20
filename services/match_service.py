from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.orm import joinedload

from models import Match, Tournament, Team
from services.base_service import BaseService
from services.notification_service import NotificationService
from services.task_service import TaskService

class MatchService(BaseService):
    def __init__(self):
        super().__init__()
        self.notification_service = NotificationService()
        self.task_service = TaskService()

    def get_match(self, match_id: int) -> Optional[Match]:
        """Pobiera mecz z relacjami"""
        try:
            return Match.query.options(
                joinedload(Match.team1),
                joinedload(Match.team2),
                joinedload(Match.tournament)
            ).get(match_id)
        except Exception as e:
            current_app.logger.error(f'Error getting match: {str(e)}')
            return None

    def get_tournament_matches(self, tournament_id: int) -> List[Match]:
        """Pobiera wszystkie mecze turnieju"""
        try:
            return Match.query.options(
                joinedload(Match.team1),
                joinedload(Match.team2)
            ).filter_by(tournament_id=tournament_id).all()
        except Exception as e:
            current_app.logger.error(f'Error getting tournament matches: {str(e)}')
            return []

    def create_match(self, tournament_id: int, team1_id: int, team2_id: int,
                    start_time: datetime, field_number: int = 1) -> Optional[Match]:
        """Tworzy nowy mecz"""
        try:
            # Sprawdź czy drużyny należą do turnieju
            tournament = Tournament.query.get(tournament_id)
            if not tournament or tournament.status != 'planned':
                return None

            team_ids = {team.id for team in tournament.teams}
            if team1_id not in team_ids or team2_id not in team_ids:
                return None

            match = Match(
                tournament_id=tournament_id,
                team1_id=team1_id,
                team2_id=team2_id,
                start_time=start_time,
                field_number=field_number,
                status='planned'
            )

            self.add(match)
            self.commit()

            # Zaplanuj powiadomienia
            self.task_service.submit_task(
                function=self.notification_service.notify_match_created,
                name=f'Powiadomienie o utworzeniu meczu {match.id}',
                args=(match.id,),
                notify_user=True
            )

            return match
        except Exception as e:
            current_app.logger.error(f'Error creating match: {str(e)}')
            self.rollback()
            return None

    def update_match_time(self, match_id: int, new_start_time: datetime) -> bool:
        """Aktualizuje czas rozpoczęcia meczu"""
        try:
            match = self.get_match(match_id)
            if not match or match.status != 'planned':
                return False

            match.start_time = new_start_time
            self.commit()

            # Powiadom o zmianie
            self.notification_service.create_notification(
                title="Zmiana czasu meczu",
                message=f"Zmieniono czas meczu {match.team1.name} vs {match.team2.name}",
                notification_type='match_time_updated'
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error updating match time: {str(e)}')
            self.rollback()
            return False

    def start_match(self, match_id: int) -> bool:
        """Rozpoczyna mecz"""
        try:
            match = self.get_match(match_id)
            if not match or match.status != 'planned':
                return False

            match.status = 'ongoing'
            match.start_time = datetime.utcnow()
            self.commit()

            # Zaplanuj powiadomienia
            self.task_service.submit_task(
                function=self.notification_service.notify_match_start,
                name=f'Powiadomienia o rozpoczęciu meczu {match_id}',
                args=(match_id,),
                notify_user=True
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error starting match: {str(e)}')
            self.rollback()
            return False

    def end_match(self, match_id: int) -> bool:
        """Kończy mecz"""
        try:
            match = self.get_match(match_id)
            if not match or match.status != 'ongoing':
                return False

            match.status = 'finished'
            self.commit()

            # Zaplanuj powiadomienia
            self.task_service.submit_task(
                function=self.notification_service.notify_match_end,
                name=f'Powiadomienia o zakończeniu meczu {match_id}',
                args=(match_id,),
                notify_user=True
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error ending match: {str(e)}')
            self.rollback()
            return False

    def update_score(self, match_id: int, team1_score: int, team2_score: int) -> bool:
        """Aktualizuje wynik meczu"""
        try:
            match = self.get_match(match_id)
            if not match or match.status == 'planned':
                return False

            match.team1_score = team1_score
            match.team2_score = team2_score
            self.commit()

            # Powiadom o aktualizacji wyniku
            self.notification_service.create_notification(
                title="Aktualizacja wyniku",
                message=f"Zaktualizowano wynik meczu {match.team1.name} vs {match.team2.name}",
                notification_type='match_score_updated'
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error updating match score: {str(e)}')
            self.rollback()
            return False

    def pause_match_timer(self, match_id: int) -> bool:
        """Zatrzymuje timer meczu"""
        try:
            match = self.get_match(match_id)
            if not match or match.status != 'ongoing':
                return False

            match.is_timer_paused = True
            match.elapsed_time = self._calculate_elapsed_time(match)
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error pausing match timer: {str(e)}')
            self.rollback()
            return False

    def resume_match_timer(self, match_id: int) -> bool:
        """Wznawia timer meczu"""
        try:
            match = self.get_match(match_id)
            if not match or match.status != 'ongoing':
                return False

            match.is_timer_paused = False
            match.start_time = datetime.utcnow() - timedelta(seconds=match.elapsed_time)
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error resuming match timer: {str(e)}')
            self.rollback()
            return False

    def _calculate_elapsed_time(self, match: Match) -> int:
        """Oblicza czas, który upłynął od rozpoczęcia meczu"""
        if match.is_timer_paused:
            return match.elapsed_time
        return int((datetime.utcnow() - match.start_time).total_seconds())

    def get_match_status(self, match_id: int) -> Dict:
        """Pobiera szczegółowy status meczu"""
        try:
            match = self.get_match(match_id)
            if not match:
                return {}

            return {
                'id': match.id,
                'tournament_id': match.tournament_id,
                'team1': {
                    'id': match.team1.id,
                    'name': match.team1.name,
                    'score': match.team1_score
                },
                'team2': {
                    'id': match.team2.id,
                    'name': match.team2.name,
                    'score': match.team2_score
                },
                'status': match.status,
                'start_time': match.start_time.isoformat() if match.start_time else None,
                'field_number': match.field_number,
                'is_timer_paused': match.is_timer_paused,
                'elapsed_time': self._calculate_elapsed_time(match) if match.status == 'ongoing' else 0
            }
        except Exception as e:
            current_app.logger.error(f'Error getting match status: {str(e)}')
            return {} 