import pytest
from datetime import datetime, date, time, timedelta
from models import Tournament, Year, Team, Match
from extensions import db

@pytest.fixture
def match_setup(app):
    """Fixture przygotowujący dane do testów meczów"""
    with app.app_context():
        # Tworzenie roku
        year = Year(year=2023)
        db.session.add(year)
        db.session.commit()

        # Tworzenie turnieju
        tournament = Tournament(
            name='Test Tournament',
            year_id=year.id,
            status='planned',
            date=date(2023, 12, 1),
            start_time=time(10, 0),
            number_of_fields=2
        )
        db.session.add(tournament)
        db.session.commit()

        # Tworzenie drużyn
        team1 = Team(name='Team 1', tournament_id=tournament.id)
        team2 = Team(name='Team 2', tournament_id=tournament.id)
        db.session.add_all([team1, team2])
        db.session.commit()

        return {
            'tournament': tournament,
            'team1': team1,
            'team2': team2
        }

def test_create_match(app, match_setup):
    """Test tworzenia meczu"""
    with app.app_context():
        match = Match(
            tournament_id=match_setup['tournament'].id,
            team1_id=match_setup['team1'].id,
            team2_id=match_setup['team2'].id,
            start_time=datetime.now(),
            status='planned'
        )
        db.session.add(match)
        db.session.commit()

        assert match.status == 'planned'
        assert match.team1_score is None
        assert match.team2_score is None
        assert match.is_timer_paused is False

def test_match_status_transitions(app, match_setup):
    """Test zmiany statusu meczu"""
    with app.app_context():
        match = Match(
            tournament_id=match_setup['tournament'].id,
            team1_id=match_setup['team1'].id,
            team2_id=match_setup['team2'].id,
            start_time=datetime.now(),
            status='planned'
        )
        db.session.add(match)
        db.session.commit()

        # Start meczu
        match.status = 'ongoing'
        db.session.commit()
        assert match.status == 'ongoing'

        # Zakończenie meczu
        match.status = 'finished'
        db.session.commit()
        assert match.status == 'finished'

def test_match_score_update(app, match_setup):
    """Test aktualizacji wyniku meczu"""
    with app.app_context():
        match = Match(
            tournament_id=match_setup['tournament'].id,
            team1_id=match_setup['team1'].id,
            team2_id=match_setup['team2'].id,
            start_time=datetime.now(),
            status='ongoing'
        )
        db.session.add(match)
        db.session.commit()

        # Aktualizacja wyniku
        match.team1_score = 2
        match.team2_score = 1
        db.session.commit()

        assert match.team1_score == 2
        assert match.team2_score == 1

def test_match_timer(app, match_setup):
    """Test timera meczu"""
    with app.app_context():
        start_time = datetime.now()
        match = Match(
            tournament_id=match_setup['tournament'].id,
            team1_id=match_setup['team1'].id,
            team2_id=match_setup['team2'].id,
            start_time=start_time,
            status='ongoing',
            is_timer_paused=False,
            elapsed_time=0
        )
        db.session.add(match)
        db.session.commit()

        # Pauza timera
        match.is_timer_paused = True
        match.elapsed_time = 300  # 5 minut
        db.session.commit()
        assert match.is_timer_paused
        assert match.elapsed_time == 300

        # Wznowienie timera
        match.is_timer_paused = False
        match.start_time = datetime.now() - timedelta(seconds=300)
        db.session.commit()
        assert not match.is_timer_paused

def test_match_validation(app, match_setup):
    """Test walidacji danych meczu"""
    with app.app_context():
        # Test meczu z tą samą drużyną
        with pytest.raises(Exception):
            match = Match(
                tournament_id=match_setup['tournament'].id,
                team1_id=match_setup['team1'].id,
                team2_id=match_setup['team1'].id,  # Ta sama drużyna
                start_time=datetime.now(),
                status='planned'
            )
            db.session.add(match)
            db.session.commit()

def test_match_relationships(app, match_setup):
    """Test relacji meczu"""
    with app.app_context():
        match = Match(
            tournament_id=match_setup['tournament'].id,
            team1_id=match_setup['team1'].id,
            team2_id=match_setup['team2'].id,
            start_time=datetime.now(),
            status='planned'
        )
        db.session.add(match)
        db.session.commit()

        # Sprawdzenie relacji
        assert match.tournament.name == 'Test Tournament'
        assert match.team1.name == 'Team 1'
        assert match.team2.name == 'Team 2'

def test_match_time_validation(app, match_setup):
    """Test walidacji czasu meczu"""
    with app.app_context():
        # Test meczu z datą w przeszłości
        with pytest.raises(Exception):
            past_time = datetime.now() - timedelta(days=1)
            match = Match(
                tournament_id=match_setup['tournament'].id,
                team1_id=match_setup['team1'].id,
                team2_id=match_setup['team2'].id,
                start_time=past_time,
                status='planned'
            )
            db.session.add(match)
            db.session.commit() 