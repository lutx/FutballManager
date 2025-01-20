from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import csv
import json
import io
import xlsxwriter
from flask import current_app
from sqlalchemy.orm import joinedload

from models import Tournament, Match, Team, User, SystemLog
from services.base_service import BaseService
from services.stats_service import StatsService

class ExportService(BaseService):
    def __init__(self):
        super().__init__()
        self.stats_service = StatsService()

    def export_tournament_to_csv(self, tournament_id: int) -> Tuple[Optional[str], str]:
        """Eksportuje dane turnieju do CSV"""
        try:
            stats = self.stats_service.get_tournament_stats(tournament_id)
            if not stats:
                return None, "Nie znaleziono turnieju"

            output = io.StringIO()
            writer = csv.writer(output)

            # Nagłówek turnieju
            writer.writerow(['Nazwa turnieju', stats['tournament_name']])
            writer.writerow(['Status', stats['status']])
            writer.writerow(['Liczba drużyn', stats['total_teams']])
            writer.writerow(['Liczba meczów', stats['total_matches']])
            writer.writerow(['Rozegrane mecze', stats['matches_played']])
            writer.writerow(['Pozostałe mecze', stats['matches_remaining']])
            writer.writerow(['Suma goli', stats['total_goals']])
            writer.writerow(['Średnia goli na mecz', stats['avg_goals_per_match']])
            writer.writerow([])  # Pusta linia

            # Tabela drużyn
            writer.writerow(['Drużyna', 'Mecze', 'Wygrane', 'Remisy', 'Przegrane', 
                           'Gole strzelone', 'Gole stracone', 'Różnica', 'Punkty'])
            for team in stats['teams']:
                writer.writerow([
                    team['team_name'],
                    team['matches_played'],
                    team['wins'],
                    team['draws'],
                    team['losses'],
                    team['goals_for'],
                    team['goals_against'],
                    team['goal_difference'],
                    team['points']
                ])

            return output.getvalue(), "text/csv"
        except Exception as e:
            current_app.logger.error(f'Error exporting tournament to CSV: {str(e)}')
            return None, "Wystąpił błąd podczas eksportu"

    def export_tournament_to_json(self, tournament_id: int) -> Tuple[Optional[str], str]:
        """Eksportuje dane turnieju do JSON"""
        try:
            stats = self.stats_service.get_tournament_stats(tournament_id)
            if not stats:
                return None, "Nie znaleziono turnieju"

            return json.dumps(stats, indent=2, ensure_ascii=False), "application/json"
        except Exception as e:
            current_app.logger.error(f'Error exporting tournament to JSON: {str(e)}')
            return None, "Wystąpił błąd podczas eksportu"

    def export_tournament_to_excel(self, tournament_id: int) -> Tuple[Optional[bytes], str]:
        """Eksportuje dane turnieju do Excel"""
        try:
            stats = self.stats_service.get_tournament_stats(tournament_id)
            if not stats:
                return None, "Nie znaleziono turnieju"

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            
            # Style
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'bg_color': '#D3D3D3'
            })
            cell_format = workbook.add_format({
                'align': 'center'
            })

            # Arkusz podsumowania
            summary_sheet = workbook.add_worksheet('Podsumowanie')
            summary_data = [
                ['Nazwa turnieju', stats['tournament_name']],
                ['Status', stats['status']],
                ['Liczba drużyn', stats['total_teams']],
                ['Liczba meczów', stats['total_matches']],
                ['Rozegrane mecze', stats['matches_played']],
                ['Pozostałe mecze', stats['matches_remaining']],
                ['Suma goli', stats['total_goals']],
                ['Średnia goli na mecz', stats['avg_goals_per_match']]
            ]
            for row, data in enumerate(summary_data):
                summary_sheet.write(row, 0, data[0], header_format)
                summary_sheet.write(row, 1, data[1], cell_format)

            # Arkusz tabeli
            table_sheet = workbook.add_worksheet('Tabela')
            headers = ['Drużyna', 'Mecze', 'Wygrane', 'Remisy', 'Przegrane', 
                      'Gole strzelone', 'Gole stracone', 'Różnica', 'Punkty']
            
            for col, header in enumerate(headers):
                table_sheet.write(0, col, header, header_format)

            for row, team in enumerate(stats['teams'], start=1):
                table_sheet.write(row, 0, team['team_name'], cell_format)
                table_sheet.write(row, 1, team['matches_played'], cell_format)
                table_sheet.write(row, 2, team['wins'], cell_format)
                table_sheet.write(row, 3, team['draws'], cell_format)
                table_sheet.write(row, 4, team['losses'], cell_format)
                table_sheet.write(row, 5, team['goals_for'], cell_format)
                table_sheet.write(row, 6, team['goals_against'], cell_format)
                table_sheet.write(row, 7, team['goal_difference'], cell_format)
                table_sheet.write(row, 8, team['points'], cell_format)

            # Dostosuj szerokość kolumn
            summary_sheet.set_column(0, 0, 20)
            summary_sheet.set_column(1, 1, 15)
            table_sheet.set_column(0, 0, 20)
            table_sheet.set_column(1, 8, 15)

            workbook.close()
            output.seek(0)
            
            return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception as e:
            current_app.logger.error(f'Error exporting tournament to Excel: {str(e)}')
            return None, "Wystąpił błąd podczas eksportu"

    def export_team_history(self, team_id: int, format: str = 'json') -> Tuple[Optional[Any], str]:
        """Eksportuje historię drużyny w wybranym formacie"""
        try:
            history = self.stats_service.get_team_history(team_id)
            if not history:
                return None, "Nie znaleziono drużyny"

            if format == 'json':
                return json.dumps(history, indent=2, default=str, ensure_ascii=False), "application/json"
            
            elif format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                
                writer.writerow(['Drużyna', history['team_name']])
                writer.writerow(['Liczba meczów', history['total_matches']])
                writer.writerow(['Gole strzelone', history['total_goals_scored']])
                writer.writerow(['Gole stracone', history['total_goals_conceded']])
                writer.writerow([])
                
                writer.writerow(['Data', 'Przeciwnik', 'Wynik', 'Gole strzelone', 'Gole stracone'])
                for match in history['matches']:
                    writer.writerow([
                        match['date'].strftime('%Y-%m-%d %H:%M'),
                        match['opponent'],
                        match['result'],
                        match['goals_scored'],
                        match['goals_conceded']
                    ])
                
                return output.getvalue(), "text/csv"
            
            else:
                return None, "Nieobsługiwany format"
        except Exception as e:
            current_app.logger.error(f'Error exporting team history: {str(e)}')
            return None, "Wystąpił błąd podczas eksportu"

    def export_global_stats(self, format: str = 'json') -> Tuple[Optional[Any], str]:
        """Eksportuje globalne statystyki w wybranym formacie"""
        try:
            stats = self.stats_service.get_global_stats()

            if format == 'json':
                return json.dumps(stats, indent=2, ensure_ascii=False), "application/json"
            
            elif format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Turnieje
                writer.writerow(['Turnieje'])
                for key, value in stats['tournaments'].items():
                    writer.writerow([key, value])
                writer.writerow([])
                
                # Mecze
                writer.writerow(['Mecze'])
                for key, value in stats['matches'].items():
                    writer.writerow([key, value])
                writer.writerow([])
                
                # Drużyny
                writer.writerow(['Drużyny'])
                for key, value in stats['teams'].items():
                    writer.writerow([key, value])
                writer.writerow([])
                
                # Użytkownicy
                writer.writerow(['Użytkownicy'])
                for key, value in stats['users'].items():
                    writer.writerow([key, value])
                
                return output.getvalue(), "text/csv"
            
            else:
                return None, "Nieobsługiwany format"
        except Exception as e:
            current_app.logger.error(f'Error exporting global stats: {str(e)}')
            return None, "Wystąpił błąd podczas eksportu"

    def log_export(self, user_email: str, export_type: str, 
                  format: str, entity_id: Optional[int] = None) -> None:
        """Loguje operację eksportu"""
        try:
            details = f'Wyeksportowano {export_type} w formacie {format}'
            if entity_id:
                details += f' (ID: {entity_id})'

            log = SystemLog(
                type='info',
                user=user_email,
                action='export_data',
                details=details
            )
            self.add(log)
            self.commit()
        except Exception as e:
            current_app.logger.error(f'Error logging export: {str(e)}') 