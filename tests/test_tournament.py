import pytest
from datetime import datetime, date, time
from models import Tournament, Year, Team, Match
from extensions import db

@pytest.fixture
def year(app):
    """Fixture tworzący rok dla testów"""
    with app.app_context():
        year = Year(year=2023)
        db.session.add(year)
        db.session.commit()
        return year

@pytest.fixture
def tournament(app, year):
    """Fixture tworzący turniej dla testów"""
    with app.app_context():
        tournament = Tournament(
            name='Test Tournament',
            year_id=year.id,
            status='planned',
            date=date(2023, 12, 1),
            address='Test Address',
            start_time=time(10, 0),
            number_of_fields=2,
            match_length=20,
            break_length=5
        )
        db.session.add(tournament)
        db.session.commit()
        return tournament

def test_create_tournament(tournament):
    """Test tworzenia turnieju"""
    assert tournament.name == 'Test Tournament'
    assert tournament.status == 'planned'
    assert tournament.number_of_fields == 2
    assert tournament.match_length == 20
    assert tournament.break_length == 5

def test_tournament_status_transitions(app, tournament):
    """Test zmiany statusu turnieju"""
    with app.app_context():
        # Start turnieju
        tournament.status = 'ongoing'
        db.session.commit()
        assert tournament.status == 'ongoing'

        # Zakończenie turnieju
        tournament.status = 'finished'
        db.session.commit()
        assert tournament.status == 'finished'

def test_tournament_teams(app, tournament):
    """Test dodawania drużyn do turnieju"""
    with app.app_context():
        # Dodaj drużyny
        team1 = Team(name='Team 1', tournament_id=tournament.id)
        team2 = Team(name='Team 2', tournament_id=tournament.id)
        db.session.add_all([team1, team2])
        db.session.commit()

        # Sprawdź czy drużyny są powiązane z turniejem
        assert len(tournament.teams) == 2
        assert tournament.teams[0].name == 'Team 1'
        assert tournament.teams[1].name == 'Team 2'

def test_tournament_matches(app, tournament):
    """Test dodawania meczów do turnieju"""
    with app.app_context():
        # Dodaj drużyny
        team1 = Team(name='Team 1', tournament_id=tournament.id)
        team2 = Team(name='Team 2', tournament_id=tournament.id)
        db.session.add_all([team1, team2])
        db.session.commit()

        # Dodaj mecz
        match = Match(
            tournament_id=tournament.id,
            team1_id=team1.id,
            team2_id=team2.id,
            start_time=datetime.now(),
            status='planned'
        )
        db.session.add(match)
        db.session.commit()

        # Sprawdź czy mecz jest powiązany z turniejem
        assert len(tournament.matches) == 1
        assert tournament.matches[0].team1.name == 'Team 1'
        assert tournament.matches[0].team2.name == 'Team 2'

def test_tournament_validation(app, year):
    """Test walidacji danych turnieju"""
    with app.app_context():
        # Test niepoprawnej daty
        with pytest.raises(Exception):
            tournament = Tournament(
                name='Invalid Tournament',
                year_id=year.id,
                date='invalid_date',
                start_time='invalid_time'
            )
            db.session.add(tournament)
            db.session.commit()

def test_tournament_unique_name_per_year(app, year):
    """Test unikalności nazwy turnieju w ramach roku"""
    with app.app_context():
        # Pierwszy turniej
        tournament1 = Tournament(
            name='Same Name',
            year_id=year.id,
            date=date(2023, 12, 1),
            start_time=time(10, 0)
        )
        db.session.add(tournament1)
        db.session.commit()

        # Próba utworzenia drugiego turnieju o tej samej nazwie w tym samym roku
        with pytest.raises(Exception):
            tournament2 = Tournament(
                name='Same Name',
                year_id=year.id,
                date=date(2023, 12, 2),
                start_time=time(11, 0)
            )
            db.session.add(tournament2)
            db.session.commit()

def test_tournament_cascade_delete(app, tournament):
    """Test kaskadowego usuwania turnieju"""
    with app.app_context():
        # Dodaj drużyny i mecze
        team1 = Team(name='Team 1', tournament_id=tournament.id)
        team2 = Team(name='Team 2', tournament_id=tournament.id)
        db.session.add_all([team1, team2])
        db.session.commit()

        match = Match(
            tournament_id=tournament.id,
            team1_id=team1.id,
            team2_id=team2.id,
            start_time=datetime.now(),
            status='planned'
        )
        db.session.add(match)
        db.session.commit()

        # Usuń turniej
        db.session.delete(tournament)
        db.session.commit()

        # Sprawdź czy drużyny i mecze zostały usunięte
        assert Team.query.count() == 0
        assert Match.query.count() == 0 