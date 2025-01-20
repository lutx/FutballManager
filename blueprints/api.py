from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import Tournament, Match, Team
from extensions import db
from services.tournament_service import TournamentService
from services.match_service import MatchService
from services.logging_service import LoggingService
from decorators import admin_required
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/tournaments/<int:tournament_id>/start', methods=['POST'])
@login_required
@admin_required
def start_tournament(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        if tournament.status != 'planned':
            return jsonify({'error': 'Turniej nie może zostać rozpoczęty'}), 400
            
        tournament.status = 'ongoing'
        tournament.start_time = datetime.utcnow()
        
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='start_tournament',
            details=f'Rozpoczęto turniej: {tournament.name}'
        )
        
        db.session.commit()
        return jsonify({'message': 'Turniej został rozpoczęty'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas rozpoczynania turnieju: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas rozpoczynania turnieju'}), 500

@bp.route('/tournaments/<int:tournament_id>/end', methods=['POST'])
@login_required
@admin_required
def end_tournament(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        if tournament.status != 'ongoing':
            return jsonify({'error': 'Turniej nie może zostać zakończony'}), 400
            
        tournament.status = 'finished'
        tournament.end_time = datetime.utcnow()
        
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='end_tournament',
            details=f'Zakończono turniej: {tournament.name}'
        )
        
        db.session.commit()
        return jsonify({'message': 'Turniej został zakończony'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas kończenia turnieju: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas kończenia turnieju'}), 500

@bp.route('/matches/<int:match_id>/start', methods=['POST'])
@login_required
@admin_required
def start_match(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        if match.status != 'planned':
            return jsonify({'error': 'Mecz nie może zostać rozpoczęty'}), 400
            
        match.status = 'ongoing'
        match.start_time = datetime.utcnow()
        
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='start_match',
            details=f'Rozpoczęto mecz: {match.team1.name} vs {match.team2.name}'
        )
        
        db.session.commit()
        return jsonify({'message': 'Mecz został rozpoczęty'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas rozpoczynania meczu: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas rozpoczynania meczu'}), 500

@bp.route('/matches/<int:match_id>/end', methods=['POST'])
@login_required
@admin_required
def end_match(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        if match.status != 'ongoing':
            return jsonify({'error': 'Mecz nie może zostać zakończony'}), 400
            
        match.status = 'finished'
        match.end_time = datetime.utcnow()
        
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='end_match',
            details=f'Zakończono mecz: {match.team1.name} vs {match.team2.name}'
        )
        
        db.session.commit()
        return jsonify({'message': 'Mecz został zakończony'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas kończenia meczu: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas kończenia meczu'}), 500

@bp.route('/matches/<int:match_id>/score', methods=['POST'])
@login_required
@admin_required
def update_score(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        if match.status != 'ongoing':
            return jsonify({'error': 'Wynik może być aktualizowany tylko podczas trwającego meczu'}), 400
            
        data = request.get_json()
        team1_score = data.get('team1_score')
        team2_score = data.get('team2_score')
        
        if team1_score is None or team2_score is None:
            return jsonify({'error': 'Brak wymaganych danych'}), 400
            
        match.team1_score = team1_score
        match.team2_score = team2_score
        
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='update_score',
            details=f'Zaktualizowano wynik meczu: {match.team1.name} {team1_score}:{team2_score} {match.team2.name}'
        )
        
        db.session.commit()
        return jsonify({'message': 'Wynik został zaktualizowany'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas aktualizacji wyniku: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas aktualizacji wyniku'}), 500

@bp.route('/tournaments/<int:tournament_id>/stats')
@login_required
def tournament_stats(tournament_id):
    try:
        stats = TournamentService.get_tournament_stats(tournament_id)
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas pobierania statystyk turnieju: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas pobierania statystyk'}), 500

@bp.route('/matches/<int:match_id>/stats')
@login_required
def match_stats(match_id):
    try:
        stats = MatchService.get_match_stats(match_id)
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas pobierania statystyk meczu: {str(e)}')
        return jsonify({'error': 'Wystąpił błąd podczas pobierania statystyk'}), 500 