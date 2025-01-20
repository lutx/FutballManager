from typing import Optional, Tuple, List
from flask import current_app
from sqlalchemy.orm import joinedload
from models import Team, Tournament, Match, SystemLog
from services.base_service import BaseService

class TeamService(BaseService):
    def get_team(self, team_id: int) -> Optional[Team]:
        return Team.query.options(
            joinedload('tournament')
        ).get(team_id)

    def get_tournament_teams(self, tournament_id: int) -> List[Team]:
        return Team.query.filter_by(tournament_id=tournament_id).all()

    def add_team(self, tournament_id: int, name: str, user_email: str) -> Tuple[bool, str]:
        try:
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return False, "Turniej nie istnieje"

            if tournament.status != 'planned':
                return False, "Można dodawać drużyny tylko do zaplanowanych turniejów"

            if not name:
                return False, "Nazwa drużyny jest wymagana"

            # Sprawdź czy drużyna o takiej nazwie już istnieje w turnieju
            existing_team = Team.query.filter_by(tournament_id=tournament_id, name=name).first()
            if existing_team:
                return False, "Drużyna o takiej nazwie już istnieje w tym turnieju"

            new_team = Team(
                name=name,
                tournament_id=tournament_id
            )
            self.add(new_team)

            log = SystemLog(
                type='info',
                user=user_email,
                action='add_team',
                details=f'Dodano nową drużynę: {name} do turnieju: {tournament.name}'
            )
            self.add(log)
            self.commit()

            return True, "Drużyna została dodana"
        except Exception as e:
            current_app.logger.error(f'Error adding team: {str(e)}')
            return False, "Wystąpił błąd podczas dodawania drużyny"

    def delete_team(self, team_id: int, user_email: str) -> Tuple[bool, str]:
        try:
            team = self.get_team(team_id)
            if not team:
                return False, "Drużyna nie istnieje"

            tournament = team.tournament
            if tournament.status != 'planned':
                return False, "Można usuwać drużyny tylko z zaplanowanych turniejów"

            # Usuń wszystkie mecze drużyny
            Match.query.filter(
                (Match.team1_id == team_id) | (Match.team2_id == team_id)
            ).delete()

            # Zapisz nazwę drużyny przed usunięciem
            team_name = team.name
            tournament_name = tournament.name

            self.delete(team)

            log = SystemLog(
                type='warning',
                user=user_email,
                action='delete_team',
                details=f'Usunięto drużynę: {team_name} z turnieju: {tournament_name}'
            )
            self.add(log)
            self.commit()

            return True, "Drużyna została usunięta"
        except Exception as e:
            current_app.logger.error(f'Error deleting team: {str(e)}')
            return False, "Wystąpił błąd podczas usuwania drużyny"

    def update_team(self, team_id: int, name: str, user_email: str) -> Tuple[bool, str]:
        try:
            team = self.get_team(team_id)
            if not team:
                return False, "Drużyna nie istnieje"

            if team.tournament.status != 'planned':
                return False, "Można edytować drużyny tylko w zaplanowanych turniejach"

            if not name:
                return False, "Nazwa drużyny jest wymagana"

            # Sprawdź czy inna drużyna w tym samym turnieju ma już taką nazwę
            existing_team = Team.query.filter_by(
                tournament_id=team.tournament_id,
                name=name
            ).filter(Team.id != team_id).first()
            
            if existing_team:
                return False, "Drużyna o takiej nazwie już istnieje w tym turnieju"

            old_name = team.name
            team.name = name

            log = SystemLog(
                type='info',
                user=user_email,
                action='edit_team',
                details=f'Zmieniono nazwę drużyny z {old_name} na {name}'
            )
            self.add(log)
            self.commit()

            return True, "Drużyna została zaktualizowana"
        except Exception as e:
            current_app.logger.error(f'Error updating team: {str(e)}')
            return False, "Wystąpił błąd podczas aktualizacji drużyny" 