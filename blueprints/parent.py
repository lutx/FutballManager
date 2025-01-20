from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from models import Year, Tournament, Team, Match, SystemSettings
from extensions import db
from services.tournament_service import TournamentService
from services.match_service import MatchService
from decorators import parent_required
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import pytz

bp = Blueprint('parent', __name__, url_prefix='/parent')

@bp.app_template_filter('format_datetime')
def format_datetime(value):
    """Format datetime for display."""
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value
            
    # Convert UTC to local time (Europe/Warsaw)
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    local_dt = value.astimezone(warsaw_tz)
    
    return local_dt.strftime('%d.%m.%Y %H:%M')

@bp.route('/')
@parent_required
def select_year():
    try:
        years = Year.query.order_by(Year.year.desc()).all()
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        # Add tournament count for each year
        for year in years:
            year.tournaments_count = len(year.tournaments)
        
        return render_template('parent/select_year.html', 
                            years=years,
                            logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania roczników: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/years/<int:year_id>')
@parent_required
def year_tournaments(year_id):
    try:
        year = Year.query.get_or_404(year_id)
        tournaments = Tournament.query.filter_by(year_id=year_id).all()
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        return render_template('parent/tournaments.html',
                            year=year,
                            tournaments=tournaments,
                            logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania turniejów: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/tournaments')
@parent_required
def tournaments():
    try:
        tournaments = Tournament.query.filter_by(status='ongoing').all()
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        return render_template('parent/tournaments.html',
                             tournaments=tournaments,
                             year=None,
                             logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania turniejów: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/tournament/<int:tournament_id>')
@parent_required
def tournament_details(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.start_time).all()
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        # Calculate team statistics
        team_stats = []
        for team in teams:
            stats = {
                'team': team,
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'points': 0
            }
            
            for match in matches:
                if match.status != 'finished':
                    continue
                
                if match.team1_id == team.id:
                    stats['goals_for'] += match.team1_score or 0
                    stats['goals_against'] += match.team2_score or 0
                    if match.team1_score > match.team2_score:
                        stats['wins'] += 1
                        stats['points'] += 3
                    elif match.team1_score == match.team2_score:
                        stats['draws'] += 1
                        stats['points'] += 1
                    else:
                        stats['losses'] += 1
                    stats['matches_played'] += 1
                elif match.team2_id == team.id:
                    stats['goals_for'] += match.team2_score or 0
                    stats['goals_against'] += match.team1_score or 0
                    if match.team2_score > match.team1_score:
                        stats['wins'] += 1
                        stats['points'] += 3
                    elif match.team1_score == match.team2_score:
                        stats['draws'] += 1
                        stats['points'] += 1
                    else:
                        stats['losses'] += 1
                    stats['matches_played'] += 1
            
            team_stats.append(stats)
        
        # Sort teams by points
        team_stats.sort(key=lambda x: (-x['points'], -(x['goals_for'] - x['goals_against']), -x['goals_for']))
        
        return render_template('parent/tournament_details.html',
                            tournament=tournament,
                            matches=matches,
                            team_stats=team_stats,
                            logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania szczegółów turnieju: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/match/<int:match_id>')
@parent_required
def match_details(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        match_stats = MatchService.get_match_stats(match_id)
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        return render_template('parent/match_details.html',
                             match=match,
                             stats=match_stats,
                             logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania szczegółów meczu: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/results')
@parent_required
def results():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        # Pobierz zakończone mecze
        matches = Match.query.filter_by(status='finished')\
            .order_by(Match.end_time.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
            
        return render_template('parent/results.html',
                             matches=matches,
                             logo_path=logo_path)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania wyników: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('main.index')) 