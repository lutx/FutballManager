from typing import Optional, Dict, List
from datetime import datetime, timedelta
from flask import current_app

from services.base_service import BaseService
from services.task_service import TaskService
from services.stats_service import StatsService
from services.notification_service import NotificationService

class ReportTaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.stats_service = StatsService()
        self.notification_service = NotificationService()

    def generate_tournament_report(self, tournament_id: int,
                                 user_id: Optional[int] = None) -> str:
        """Rozpoczyna zadanie generowania raportu turnieju"""
        try:
            task_id = self.task_service.submit_task(
                function=self._generate_tournament_report,
                name=f'Raport turnieju {tournament_id}',
                description=f'Generowanie szczegółowego raportu dla turnieju {tournament_id}',
                args=(tournament_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error starting tournament report task: {str(e)}')
            raise

    def _generate_tournament_report(self, tournament_id: int) -> Dict:
        """Generuje szczegółowy raport turnieju"""
        try:
            # Pobierz podstawowe statystyki turnieju
            tournament_stats = self.stats_service.get_tournament_stats(tournament_id)
            
            # Pobierz statystyki dla każdej drużyny
            team_stats = []
            for team in tournament_stats['teams']:
                team_history = self.stats_service.get_team_history(team['id'])
                team_stats.append({
                    'team': team,
                    'history': team_history
                })

            # Przeanalizuj trendy i wzorce
            trends = self._analyze_tournament_trends(tournament_stats, team_stats)

            return {
                'tournament': tournament_stats,
                'team_stats': team_stats,
                'trends': trends,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error generating tournament report: {str(e)}')
            raise

    def _analyze_tournament_trends(self, tournament_stats: Dict,
                                 team_stats: List[Dict]) -> Dict:
        """Analizuje trendy w turnieju"""
        try:
            return {
                'scoring_trends': self._analyze_scoring_trends(tournament_stats),
                'performance_trends': self._analyze_team_performance(team_stats),
                'match_patterns': self._analyze_match_patterns(tournament_stats)
            }
        except Exception as e:
            current_app.logger.error(f'Error analyzing tournament trends: {str(e)}')
            raise

    def _analyze_scoring_trends(self, tournament_stats: Dict) -> Dict:
        """Analizuje trendy w zdobywaniu punktów"""
        try:
            matches = tournament_stats.get('matches', [])
            if not matches:
                return {}

            total_goals = sum(match['home_score'] + match['away_score'] 
                            for match in matches if match['status'] == 'completed')
            avg_goals = total_goals / len(matches) if matches else 0

            return {
                'total_goals': total_goals,
                'average_goals_per_match': avg_goals,
                'high_scoring_matches': len([m for m in matches 
                    if m['status'] == 'completed' and 
                    (m['home_score'] + m['away_score']) > avg_goals]),
                'low_scoring_matches': len([m for m in matches 
                    if m['status'] == 'completed' and 
                    (m['home_score'] + m['away_score']) < avg_goals])
            }
        except Exception as e:
            current_app.logger.error(f'Error analyzing scoring trends: {str(e)}')
            raise

    def _analyze_team_performance(self, team_stats: List[Dict]) -> Dict:
        """Analizuje wydajność drużyn"""
        try:
            performances = []
            for team in team_stats:
                history = team['history']
                recent_matches = history.get('recent_matches', [])
                if not recent_matches:
                    continue

                # Oblicz trend formy
                form_trend = 0
                for match in recent_matches:
                    if match['result'] == 'win':
                        form_trend += 1
                    elif match['result'] == 'loss':
                        form_trend -= 1

                performances.append({
                    'team_id': team['team']['id'],
                    'team_name': team['team']['name'],
                    'form_trend': form_trend,
                    'consistency': self._calculate_consistency(recent_matches)
                })

            return {
                'team_performances': performances,
                'most_consistent': max(performances, key=lambda x: x['consistency']) 
                    if performances else None,
                'least_consistent': min(performances, key=lambda x: x['consistency'])
                    if performances else None
            }
        except Exception as e:
            current_app.logger.error(f'Error analyzing team performance: {str(e)}')
            raise

    def _calculate_consistency(self, matches: List[Dict]) -> float:
        """Oblicza wskaźnik konsystencji drużyny"""
        try:
            if not matches:
                return 0.0

            # Oblicz odchylenie standardowe wyników
            results = [1 if m['result'] == 'win' else 0 if m['result'] == 'loss' 
                      else 0.5 for m in matches]
            mean = sum(results) / len(results)
            variance = sum((x - mean) ** 2 for x in results) / len(results)
            
            # Przekształć na wskaźnik 0-1 (gdzie 1 to najwyższa konsystencja)
            return 1 - (variance ** 0.5)
        except Exception as e:
            current_app.logger.error(f'Error calculating consistency: {str(e)}')
            return 0.0

    def _analyze_match_patterns(self, tournament_stats: Dict) -> Dict:
        """Analizuje wzorce w meczach"""
        try:
            matches = tournament_stats.get('matches', [])
            if not matches:
                return {}

            completed_matches = [m for m in matches if m['status'] == 'completed']
            
            # Analiza czasu goli
            first_half_goals = 0
            second_half_goals = 0
            comebacks = 0
            
            for match in completed_matches:
                # Tutaj możemy dodać więcej szczegółowej analizy
                if match.get('first_half_goals'):
                    first_half_goals += match['first_half_goals']
                if match.get('second_half_goals'):
                    second_half_goals += match['second_half_goals']
                if match.get('had_comeback'):
                    comebacks += 1

            return {
                'first_half_goals': first_half_goals,
                'second_half_goals': second_half_goals,
                'comebacks': comebacks,
                'total_matches': len(completed_matches)
            }
        except Exception as e:
            current_app.logger.error(f'Error analyzing match patterns: {str(e)}')
            raise

    def generate_team_report(self, team_id: int, user_id: Optional[int] = None) -> str:
        """Rozpoczyna zadanie generowania raportu drużyny"""
        try:
            task_id = self.task_service.submit_task(
                function=self._generate_team_report,
                name=f'Raport drużyny {team_id}',
                description=f'Generowanie szczegółowego raportu dla drużyny {team_id}',
                args=(team_id,),
                user_id=user_id,
                notify_user=True
            )

            return task_id
        except Exception as e:
            current_app.logger.error(f'Error starting team report task: {str(e)}')
            raise

    def _generate_team_report(self, team_id: int) -> Dict:
        """Generuje szczegółowy raport drużyny"""
        try:
            # Pobierz historię drużyny
            team_history = self.stats_service.get_team_history(team_id)
            
            # Analizuj wydajność w różnych turniejach
            tournament_performance = self._analyze_tournament_performance(team_history)
            
            # Analizuj trendy strzeleckie
            scoring_analysis = self._analyze_team_scoring(team_history)
            
            return {
                'team': team_history['team'],
                'overall_stats': team_history['stats'],
                'tournament_performance': tournament_performance,
                'scoring_analysis': scoring_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f'Error generating team report: {str(e)}')
            raise

    def get_report_task_status(self, task_id: str) -> Optional[Dict]:
        """Pobiera status zadania generowania raportu"""
        return self.task_service.get_task_status(task_id)

    def cancel_report_task(self, task_id: str) -> bool:
        """Anuluje zadanie generowania raportu"""
        return self.task_service.cancel_task(task_id)

    def get_user_report_tasks(self, user_id: int, limit: int = 50) -> list:
        """Pobiera listę zadań generowania raportów użytkownika"""
        return self.task_service.get_user_tasks(
            user_id=user_id,
            limit=limit
        ) 