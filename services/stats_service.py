from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from flask import current_app

from models import Tournament, Match, Team, User, SystemLog
from services.base_service import BaseService

class StatsService(BaseService):
    def get_tournament_stats(self, tournament_id: int) -> Optional[Dict]:
        """Generuje szczegółowe statystyki turnieju"""
        try:
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return None

            matches = Match.query.filter_by(tournament_id=tournament_id).all()
            teams = Team.query.filter_by(tournament_id=tournament_id).all()

            stats = {
                'tournament_name': tournament.name,
                'status': tournament.status,
                'total_teams': len(teams),
                'total_matches': len(matches),
                'matches_played': len([m for m in matches if m.status == 'finished']),
                'matches_remaining': len([m for m in matches if m.status != 'finished']),
                'total_goals': sum((m.team1_score or 0) + (m.team2_score or 0) for m in matches if m.status == 'finished'),
                'avg_goals_per_match': 0,
                'teams': []
            }

            if stats['matches_played'] > 0:
                stats['avg_goals_per_match'] = round(stats['total_goals'] / stats['matches_played'], 2)

            # Statystyki drużyn
            for team in teams:
                team_matches = [m for m in matches if m.team1_id == team.id or m.team2_id == team.id]
                team_stats = {
                    'team_name': team.name,
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'goal_difference': 0,
                    'points': 0
                }

                for match in team_matches:
                    if match.status != 'finished':
                        continue

                    team_stats['matches_played'] += 1
                    if match.team1_id == team.id:
                        team_stats['goals_for'] += match.team1_score or 0
                        team_stats['goals_against'] += match.team2_score or 0
                        if match.team1_score > match.team2_score:
                            team_stats['wins'] += 1
                            team_stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            team_stats['draws'] += 1
                            team_stats['points'] += 1
                        else:
                            team_stats['losses'] += 1
                    else:
                        team_stats['goals_for'] += match.team2_score or 0
                        team_stats['goals_against'] += match.team1_score or 0
                        if match.team2_score > match.team1_score:
                            team_stats['wins'] += 1
                            team_stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            team_stats['draws'] += 1
                            team_stats['points'] += 1
                        else:
                            team_stats['losses'] += 1

                team_stats['goal_difference'] = team_stats['goals_for'] - team_stats['goals_against']
                stats['teams'].append(team_stats)

            # Sortowanie drużyn według punktów i różnicy bramek
            stats['teams'].sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

            return stats
        except Exception as e:
            current_app.logger.error(f'Error getting tournament stats: {str(e)}')
            return None

    def get_team_history(self, team_id: int) -> Optional[Dict]:
        """Pobiera historię meczów drużyny"""
        try:
            team = Team.query.get(team_id)
            if not team:
                return None

            matches = Match.query.filter(
                and_(
                    Match.status == 'finished',
                    (Match.team1_id == team_id) | (Match.team2_id == team_id)
                )
            ).order_by(Match.start_time).all()

            history = {
                'team_name': team.name,
                'matches': [],
                'total_matches': len(matches),
                'total_goals_scored': 0,
                'total_goals_conceded': 0,
                'form_last_5': []  # W, D, L dla ostatnich 5 meczów
            }

            for match in matches:
                match_result = {
                    'date': match.start_time,
                    'opponent': match.team2.name if match.team1_id == team_id else match.team1.name,
                    'goals_scored': match.team1_score if match.team1_id == team_id else match.team2_score,
                    'goals_conceded': match.team2_score if match.team1_id == team_id else match.team1_score,
                }

                if match.team1_id == team_id:
                    if match.team1_score > match.team2_score:
                        match_result['result'] = 'W'
                    elif match.team1_score < match.team2_score:
                        match_result['result'] = 'L'
                    else:
                        match_result['result'] = 'D'
                else:
                    if match.team2_score > match.team1_score:
                        match_result['result'] = 'W'
                    elif match.team2_score < match.team1_score:
                        match_result['result'] = 'L'
                    else:
                        match_result['result'] = 'D'

                history['matches'].append(match_result)
                history['total_goals_scored'] += match_result['goals_scored'] or 0
                history['total_goals_conceded'] += match_result['goals_conceded'] or 0
                
                if len(history['form_last_5']) < 5:
                    history['form_last_5'].append(match_result['result'])

            return history
        except Exception as e:
            current_app.logger.error(f'Error getting team history: {str(e)}')
            return None

    def get_match_stats(self, match_id: int) -> Optional[Dict]:
        """Pobiera szczegółowe statystyki meczu"""
        try:
            match = Match.query.get(match_id)
            if not match:
                return None

            stats = {
                'match_id': match.id,
                'tournament': match.tournament.name,
                'team1': {
                    'name': match.team1.name,
                    'score': match.team1_score or 0,
                },
                'team2': {
                    'name': match.team2.name,
                    'score': match.team2_score or 0,
                },
                'status': match.status,
                'start_time': match.start_time,
                'duration': match.elapsed_time if match.status == 'finished' else None,
                'winner': None,
                'total_goals': (match.team1_score or 0) + (match.team2_score or 0)
            }

            if match.status == 'finished':
                if match.team1_score > match.team2_score:
                    stats['winner'] = match.team1.name
                elif match.team2_score > match.team1_score:
                    stats['winner'] = match.team2.name
                else:
                    stats['winner'] = 'Remis'

            return stats
        except Exception as e:
            current_app.logger.error(f'Error getting match stats: {str(e)}')
            return None

    def get_global_stats(self) -> Dict:
        """Pobiera globalne statystyki systemu"""
        try:
            stats = {
                'tournaments': {
                    'total': Tournament.query.count(),
                    'ongoing': Tournament.query.filter_by(status='ongoing').count(),
                    'finished': Tournament.query.filter_by(status='finished').count(),
                    'planned': Tournament.query.filter_by(status='planned').count()
                },
                'matches': {
                    'total': Match.query.count(),
                    'finished': Match.query.filter_by(status='finished').count(),
                    'ongoing': Match.query.filter_by(status='ongoing').count(),
                    'planned': Match.query.filter_by(status='planned').count(),
                    'total_goals': Match.query.with_entities(
                        func.sum(Match.team1_score), 
                        func.sum(Match.team2_score)
                    ).first()
                },
                'teams': {
                    'total': Team.query.count(),
                    'avg_per_tournament': 0
                },
                'users': {
                    'total': User.query.count(),
                    'active': User.query.filter_by(is_active=True).count()
                }
            }

            # Oblicz średnią liczbę drużyn na turniej
            if stats['tournaments']['total'] > 0:
                stats['teams']['avg_per_tournament'] = round(
                    stats['teams']['total'] / stats['tournaments']['total'], 
                    2
                )

            # Oblicz całkowitą liczbę goli
            total_goals = sum(x or 0 for x in stats['matches']['total_goals'] if x is not None)
            stats['matches']['total_goals'] = total_goals

            # Oblicz średnią liczbę goli na mecz
            if stats['matches']['finished'] > 0:
                stats['matches']['avg_goals_per_match'] = round(
                    total_goals / stats['matches']['finished'],
                    2
                )

            return stats
        except Exception as e:
            current_app.logger.error(f'Error getting global stats: {str(e)}')
            return {
                'tournaments': {'total': 0, 'ongoing': 0, 'finished': 0, 'planned': 0},
                'matches': {'total': 0, 'finished': 0, 'ongoing': 0, 'planned': 0, 'total_goals': 0},
                'teams': {'total': 0, 'avg_per_tournament': 0},
                'users': {'total': 0, 'active': 0}
            } 