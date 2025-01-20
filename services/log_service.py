from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import desc
from flask import current_app

from models import SystemLog
from services.base_service import BaseService

class LogService(BaseService):
    def get_logs(self, page: int = 1, per_page: int = 50, 
                 log_type: Optional[str] = None,
                 action: Optional[str] = None,
                 user_email: Optional[str] = None,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None) -> Tuple[List[SystemLog], int]:
        """
        Pobiera logi z możliwością filtrowania i paginacji
        Zwraca tuple (lista logów, całkowita liczba logów)
        """
        try:
            query = SystemLog.query

            if log_type:
                query = query.filter(SystemLog.type == log_type)
            if action:
                query = query.filter(SystemLog.action == action)
            if user_email:
                query = query.filter(SystemLog.user == user_email)
            if start_date:
                query = query.filter(SystemLog.timestamp >= start_date)
            if end_date:
                query = query.filter(SystemLog.timestamp <= end_date)

            # Sortowanie od najnowszych
            query = query.order_by(desc(SystemLog.timestamp))

            # Paginacja
            total = query.count()
            logs = query.offset((page - 1) * per_page).limit(per_page).all()

            return logs, total
        except Exception as e:
            current_app.logger.error(f'Error getting logs: {str(e)}')
            return [], 0

    def get_log_types(self) -> List[str]:
        """Pobiera unikalne typy logów"""
        try:
            return [r[0] for r in SystemLog.query.with_entities(SystemLog.type).distinct()]
        except Exception as e:
            current_app.logger.error(f'Error getting log types: {str(e)}')
            return []

    def get_log_actions(self) -> List[str]:
        """Pobiera unikalne akcje z logów"""
        try:
            return [r[0] for r in SystemLog.query.with_entities(SystemLog.action).distinct()]
        except Exception as e:
            current_app.logger.error(f'Error getting log actions: {str(e)}')
            return []

    def get_recent_user_actions(self, user_email: str, hours: int = 24) -> List[SystemLog]:
        """Pobiera ostatnie akcje użytkownika z określonego okresu"""
        try:
            start_date = datetime.utcnow() - timedelta(hours=hours)
            return SystemLog.query.filter(
                SystemLog.user == user_email,
                SystemLog.timestamp >= start_date
            ).order_by(desc(SystemLog.timestamp)).all()
        except Exception as e:
            current_app.logger.error(f'Error getting recent user actions: {str(e)}')
            return []

    def get_activity_summary(self, days: int = 7) -> dict:
        """
        Tworzy podsumowanie aktywności z ostatnich dni
        Zwraca słownik z licznikami dla różnych typów akcji
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            logs = SystemLog.query.filter(SystemLog.timestamp >= start_date).all()

            summary = {
                'total_actions': len(logs),
                'by_type': {},
                'by_action': {},
                'by_user': {}
            }

            for log in logs:
                # Liczenie według typu
                if log.type not in summary['by_type']:
                    summary['by_type'][log.type] = 0
                summary['by_type'][log.type] += 1

                # Liczenie według akcji
                if log.action not in summary['by_action']:
                    summary['by_action'][log.action] = 0
                summary['by_action'][log.action] += 1

                # Liczenie według użytkownika
                if log.user not in summary['by_user']:
                    summary['by_user'][log.user] = 0
                summary['by_user'][log.user] += 1

            return summary
        except Exception as e:
            current_app.logger.error(f'Error getting activity summary: {str(e)}')
            return {
                'total_actions': 0,
                'by_type': {},
                'by_action': {},
                'by_user': {}
            }

    def clear_old_logs(self, days: int = 90) -> Tuple[bool, str]:
        """Usuwa stare logi starsze niż określona liczba dni"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = SystemLog.query.filter(
                SystemLog.timestamp < cutoff_date
            ).delete()

            log = SystemLog(
                type='warning',
                user='system',
                action='clear_old_logs',
                details=f'Usunięto {deleted} starych logów starszych niż {days} dni'
            )
            self.add(log)
            self.commit()

            return True, f"Usunięto {deleted} starych logów"
        except Exception as e:
            current_app.logger.error(f'Error clearing old logs: {str(e)}')
            return False, "Wystąpił błąd podczas czyszczenia starych logów"

    def add_system_log(self, log_type: str, action: str, details: str, 
                      user: str = 'system') -> bool:
        """Dodaje nowy log systemowy"""
        try:
            log = SystemLog(
                type=log_type,
                user=user,
                action=action,
                details=details
            )
            self.add(log)
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error adding system log: {str(e)}')
            return False 