from typing import Optional, Dict, List
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.orm import joinedload

from models import Tournament, Team, Match, Year, TournamentStanding
from services.base_service import BaseService
from services.notification_service import NotificationService
from services.task_service import TaskService

class TournamentService(BaseService):
    def __init__(self):
        super().__init__()
        self.notification_service = NotificationService()
        self.task_service = TaskService()

    def create_tournament(self, name: str, year_id: int, date: datetime,
                        address: str, start_time: datetime,
                        number_of_fields: int = 1,
                        match_length: int = 20,
                        break_length: int = 5) -> Tournament:
        """Tworzy nowy turniej"""
        try:
            tournament = Tournament(
                name=name,
                year_id=year_id,
                date=date,
                address=address,
                start_time=start_time.time(),
                number_of_fields=number_of_fields,
                match_length=match_length,
                break_length=break_length,
                status='planned'
            )
            
            self.add(tournament)
            self.commit()

            # Powiadom o utworzeniu turnieju
            self.notification_service.create_notification(
                title="Nowy turniej",
                message=f"Utworzono nowy turniej: {name}",
                notification_type='tournament_created'
            )

            return tournament
        except Exception as e:
            current_app.logger.error(f'Error creating tournament: {str(e)}')
            self.rollback()
            raise

    def get_tournament(self, tournament_id: int) -> Optional[Tournament]:
        """Pobiera turniej z relacjami"""
        try:
            return Tournament.query.options(
                joinedload(Tournament.teams),
                joinedload(Tournament.matches).joinedload(Match.team1),
                joinedload(Tournament.matches).joinedload(Match.team2)
            ).get(tournament_id)
        except Exception as e:
            current_app.logger.error(f'Error getting tournament: {str(e)}')
            return None

    def get_tournaments_by_year(self, year_id: int) -> List[Tournament]:
        """Pobiera turnieje z danego roku"""
        try:
            return Tournament.query.filter_by(year_id=year_id).all()
        except Exception as e:
            current_app.logger.error(f'Error getting tournaments by year: {str(e)}')
            return []

    def update_tournament(self, tournament_id: int, **kwargs) -> bool:
        """Aktualizuje dane turnieju"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament:
                return False

            # Aktualizuj pola
            for key, value in kwargs.items():
                if hasattr(tournament, key):
                    setattr(tournament, key, value)

            self.commit()

            # Powiadom o aktualizacji (bez user_id dla powiadomień systemowych)
            self.notification_service.create_notification(
                title="Aktualizacja turnieju",
                message=f"Zaktualizowano turniej: {tournament.name}",
                notification_type='tournament_updated',
                user_id=None  # Systemowe powiadomienie
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error updating tournament: {str(e)}')
            self.session.rollback()  # Use session.rollback() from BaseService
            return False

    def start_tournament(self, tournament_id: int) -> bool:
        """Rozpoczyna turniej"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament or tournament.status != 'planned':
                return False

            tournament.status = 'ongoing'
            self.commit()

            # Zaplanuj powiadomienia
            self.task_service.submit_task(
                function=self.notification_service.notify_tournament_start,
                name=f'Powiadomienia o rozpoczęciu turnieju {tournament_id}',
                args=(tournament_id,),
                notify_user=True
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error starting tournament: {str(e)}')
            self.rollback()
            return False

    def end_tournament(self, tournament_id: int) -> bool:
        """Kończy turniej"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament or tournament.status != 'ongoing':
                return False

            # Sprawdź czy wszystkie mecze są zakończone
            unfinished_matches = Match.query.filter_by(
                tournament_id=tournament_id,
                status='ongoing'
            ).count()

            if unfinished_matches > 0:
                return False

            tournament.status = 'finished'
            self.commit()

            # Zaplanuj powiadomienia i archiwizację
            self.task_service.submit_task(
                function=self.notification_service.notify_tournament_end,
                name=f'Powiadomienia o zakończeniu turnieju {tournament_id}',
                args=(tournament_id,),
                notify_user=True
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error ending tournament: {str(e)}')
            self.rollback()
            return False

    def add_team_to_tournament(self, tournament_id: int, team_name: str) -> Optional[Team]:
        """Dodaje drużynę do turnieju"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament or tournament.status != 'planned':
                return None

            team = Team(name=team_name, tournament_id=tournament_id)
            self.add(team)
            self.commit()

            return team
        except Exception as e:
            current_app.logger.error(f'Error adding team to tournament: {str(e)}')
            self.rollback()
            return None

    def remove_team_from_tournament(self, tournament_id: int, team_id: int) -> bool:
        """Usuwa drużynę z turnieju"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament or tournament.status != 'planned':
                return False

            # Sprawdź czy drużyna ma zaplanowane mecze
            has_matches = Match.query.filter(
                (Match.team1_id == team_id) | (Match.team2_id == team_id)
            ).count() > 0

            if has_matches:
                return False

            Team.query.filter_by(id=team_id, tournament_id=tournament_id).delete()
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error removing team from tournament: {str(e)}')
            self.rollback()
            return False

    def generate_matches(self, tournament_id: int) -> bool:
        """Generuje mecze dla turnieju z uwzględnieniem wielu boisk"""
        try:
            tournament = self.get_tournament(tournament_id)
            if not tournament or tournament.status != 'planned':
                return False

            teams = tournament.teams
            if len(teams) < 2:
                return False

            # Generuj wszystkie możliwe pary drużyn
            matches_to_generate = []
            for i, team1 in enumerate(teams):
                for team2 in teams[i+1:]:
                    matches_to_generate.append((team1, team2))

            # Oblicz czas trwania meczu i przerwy
            match_duration = timedelta(minutes=tournament.match_length)
            break_duration = timedelta(minutes=tournament.break_length)
            
            # Inicjalizuj czas rozpoczęcia i numery boisk
            if not tournament.start_time:
                return False
                
            start_time = tournament.start_time
            available_fields = list(range(1, tournament.number_of_fields + 1))
            field_times = {field: start_time for field in available_fields}
            
            # Generuj mecze, przydzielając je do pierwszego dostępnego boiska
            matches = []
            for team1, team2 in matches_to_generate:
                # Znajdź najbliższe dostępne boisko
                field_number = min(field_times, key=field_times.get)
                match_start_time = field_times[field_number]
                
                # Stwórz mecz
                match = Match(
                    tournament_id=tournament_id,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    start_time=match_start_time,
                    field_number=field_number,
                    status='planned'
                )
                matches.append(match)
                
                # Zaktualizuj czas dla tego boiska
                field_times[field_number] = match_start_time + match_duration + break_duration

            # Usuń istniejące mecze
            Match.query.filter_by(tournament_id=tournament_id).delete()
            
            # Zapisz wszystkie mecze
            for match in matches:
                self.add(match)
            self.commit()

            # Powiadom o wygenerowaniu meczów
            self.notification_service.create_notification(
                title="Wygenerowano mecze",
                message=f"Wygenerowano {len(matches)} meczów dla turnieju: {tournament.name}",
                notification_type='matches_generated',
                user_id=None  # Systemowe powiadomienie
            )

            return True
        except Exception as e:
            current_app.logger.error(f'Error generating matches: {str(e)}')
            self.session.rollback()  # Use session.rollback() from BaseService
            return False

    def get_tournament_standings(self, tournament_id: int) -> List[Dict]:
        """Pobiera aktualną tabelę wyników turnieju"""
        try:
            standings = TournamentStanding.query.filter_by(tournament_id=tournament_id)\
                .order_by(TournamentStanding.position).all()
            
            if not standings:
                return []
            
            result = []
            for standing in standings:
                team = standing.team
                result.append({
                    'team': {
                        'id': team.id,
                        'name': team.name
                    },
                    'history': {
                        'stats': {
                            'matches_played': standing.matches_played,
                            'wins': standing.wins,
                            'draws': standing.draws,
                            'losses': standing.losses,
                            'goals_scored': standing.goals_for,
                            'goals_conceded': standing.goals_against,
                            'points': standing.points
                        }
                    },
                    'position': standing.position
                })
            
            return result
        except Exception as e:
            current_app.logger.error(f'Error getting tournament standings: {str(e)}')
            return [] 