from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import Tournament, Match, Team, SystemLog
from extensions import db, limiter
from services.tournament_service import TournamentService
from services.match_service import MatchService
from services.logging_service import LoggingService
from decorators import admin_required
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from services.cache_service import CacheService
import json

bp = Blueprint('api', __name__, url_prefix='/api')

# Rate limiting for API endpoints
@bp.before_request
def before_request():
    pass

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

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

@bp.route('/matches/<int:match_id>/status', methods=['GET'])
@limiter.limit("30 per minute")
def get_match_status(match_id):
    """Get current match status and score for real-time updates."""
    try:
        match = Match.query.get_or_404(match_id)
        
        return jsonify({
            'match_id': match.id,
            'status': match.status,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'elapsed_time': match.elapsed_time,
            'is_timer_paused': match.is_timer_paused,
            'last_updated': datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Error getting match status: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/matches/<int:match_id>/events', methods=['GET'])
@limiter.limit("20 per minute")
def get_match_events(match_id):
    """Get match events for real-time updates."""
    try:
        # This would typically get events from a match events table
        # For now, return basic match info
        match = Match.query.get_or_404(match_id)
        
        events = []
        if match.team1_score is not None and match.team2_score is not None:
            events.append({
                'type': 'score_update',
                'timestamp': datetime.utcnow().isoformat(),
                'team1_score': match.team1_score,
                'team2_score': match.team2_score
            })
        
        return jsonify({
            'match_id': match.id,
            'events': events
        })
    except Exception as e:
        current_app.logger.error(f'Error getting match events: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tournaments/<int:tournament_id>/standings', methods=['GET'])
@limiter.limit("10 per minute")
def get_tournament_standings(tournament_id):
    """Get cached tournament standings."""
    try:
        # Use cache service for performance
        standings = CacheService.get_team_standings(tournament_id)
        
        return jsonify({
            'tournament_id': tournament_id,
            'standings': standings,
            'last_updated': datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Error getting tournament standings: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tournaments/<int:tournament_id>/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_tournament_stats(tournament_id):
    """Get cached tournament statistics."""
    try:
        # Use cache service for performance
        stats = CacheService.get_tournament_stats(tournament_id)
        
        return jsonify({
            'tournament_id': tournament_id,
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f'Error getting tournament stats: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/matches/<int:match_id>/update', methods=['POST'])
@login_required
@admin_required
@limiter.limit("60 per minute")
def update_match_score(match_id):
    """Update match score via API."""
    try:
        match = Match.query.get_or_404(match_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input
        team1_score = data.get('team1_score')
        team2_score = data.get('team2_score')
        
        if team1_score is not None:
            if not isinstance(team1_score, int) or team1_score < 0:
                return jsonify({'error': 'Invalid team1_score'}), 400
            match.team1_score = team1_score
        
        if team2_score is not None:
            if not isinstance(team2_score, int) or team2_score < 0:
                return jsonify({'error': 'Invalid team2_score'}), 400
            match.team2_score = team2_score
        
        # Update elapsed time if provided
        elapsed_time = data.get('elapsed_time')
        if elapsed_time is not None:
            if not isinstance(elapsed_time, int) or elapsed_time < 0:
                return jsonify({'error': 'Invalid elapsed_time'}), 400
            match.elapsed_time = elapsed_time
        
        db.session.commit()
        
        # Invalidate cache for this tournament
        CacheService.invalidate_tournament_cache(match.tournament_id)
        
        # Log the update
        LoggingService.add_log(
            type='info',
            user=current_user.email,
            action='api_match_update',
            details=f'Updated score for match {match_id}: {team1_score}-{team2_score}'
        )
        
        return jsonify({
            'success': True,
            'match_id': match.id,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'elapsed_time': match.elapsed_time,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating match score via API: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/cache/stats', methods=['GET'])
@login_required
@admin_required
def get_cache_stats():
    """Get cache statistics for monitoring."""
    try:
        stats = CacheService.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f'Error getting cache stats: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/cache/clear', methods=['POST'])
@login_required
@admin_required
def clear_cache():
    """Clear application cache."""
    try:
        CacheService.clear()
        
        LoggingService.add_log(
            type='warning',
            user=current_user.email,
            action='cache_clear',
            details='Application cache cleared'
        )
        
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        current_app.logger.error(f'Error clearing cache: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/system/logs', methods=['GET'])
@login_required
@admin_required
@limiter.limit("10 per minute")
def get_system_logs():
    """Get recent system logs via API."""
    try:
        limit = request.args.get('limit', 50, type=int)
        if limit > 100:
            limit = 100  # Cap at 100 for performance
        
        logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'logs': [{
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'type': log.type,
                'user': log.user,
                'action': log.action,
                'details': log.details
            } for log in logs]
        })
    except Exception as e:
        current_app.logger.error(f'Error getting system logs: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers for API
@bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@bp.errorhandler(400)
def api_bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@bp.errorhandler(429)
def api_rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded'}), 429 