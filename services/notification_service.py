from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import desc
from flask import current_app
from sqlalchemy.orm import joinedload

from models import Notification, User, Tournament, Match, SystemLog
from services.base_service import BaseService

class NotificationService(BaseService):
    def get_user_notifications(self, user_id: int, page: int = 1, 
                             per_page: int = 20) -> Tuple[List[Notification], int]:
        """Pobiera powiadomienia użytkownika z paginacją"""
        try:
            query = Notification.query.filter_by(user_id=user_id)\
                .order_by(desc(Notification.created_at))
            
            total = query.count()
            notifications = query.offset((page - 1) * per_page).limit(per_page).all()
            
            return notifications, total
        except Exception as e:
            current_app.logger.error(f'Error getting user notifications: {str(e)}')
            return [], 0

    def get_unread_count(self, user_id: int) -> int:
        """Pobiera liczbę nieprzeczytanych powiadomień"""
        try:
            return Notification.query.filter_by(
                user_id=user_id,
                is_read=False
            ).count()
        except Exception as e:
            current_app.logger.error(f'Error getting unread count: {str(e)}')
            return 0

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Oznacza powiadomienie jako przeczytane"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id,
                user_id=user_id
            ).first()
            
            if notification and not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error marking notification as read: {str(e)}')
            return False

    def mark_all_as_read(self, user_id: int) -> bool:
        """Oznacza wszystkie powiadomienia użytkownika jako przeczytane"""
        try:
            Notification.query.filter_by(
                user_id=user_id,
                is_read=False
            ).update({
                'is_read': True,
                'read_at': datetime.utcnow()
            })
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error marking all notifications as read: {str(e)}')
            return False

    def create_notification(self, user_id: int, title: str, message: str, 
                          notification_type: str, related_id: Optional[int] = None) -> bool:
        """Tworzy nowe powiadomienie dla użytkownika"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                related_id=related_id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            self.add(notification)
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error creating notification: {str(e)}')
            return False

    def notify_match_start(self, match_id: int) -> bool:
        """Powiadamia o rozpoczęciu meczu"""
        try:
            match = Match.query.options(
                joinedload('team1'),
                joinedload('team2'),
                joinedload('tournament')
            ).get(match_id)
            
            if not match:
                return False

            # Znajdź użytkowników do powiadomienia (np. administratorów turnieju)
            users = User.query.filter_by(is_active=True).all()
            
            title = "Rozpoczęcie meczu"
            message = f"Mecz {match.team1.name} vs {match.team2.name} w turnieju {match.tournament.name} właśnie się rozpoczął"
            
            for user in users:
                self.create_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type='match_start',
                    related_id=match_id
                )
            return True
        except Exception as e:
            current_app.logger.error(f'Error notifying match start: {str(e)}')
            return False

    def notify_match_end(self, match_id: int) -> bool:
        """Powiadamia o zakończeniu meczu"""
        try:
            match = Match.query.options(
                joinedload('team1'),
                joinedload('team2'),
                joinedload('tournament')
            ).get(match_id)
            
            if not match:
                return False

            users = User.query.filter_by(is_active=True).all()
            
            title = "Zakończenie meczu"
            message = f"Mecz {match.team1.name} vs {match.team2.name} zakończył się wynikiem {match.team1_score}:{match.team2_score}"
            
            for user in users:
                self.create_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type='match_end',
                    related_id=match_id
                )
            return True
        except Exception as e:
            current_app.logger.error(f'Error notifying match end: {str(e)}')
            return False

    def notify_tournament_start(self, tournament_id: int) -> bool:
        """Powiadamia o rozpoczęciu turnieju"""
        try:
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return False

            users = User.query.filter_by(is_active=True).all()
            
            title = "Rozpoczęcie turnieju"
            message = f"Turniej {tournament.name} właśnie się rozpoczął"
            
            for user in users:
                self.create_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type='tournament_start',
                    related_id=tournament_id
                )
            return True
        except Exception as e:
            current_app.logger.error(f'Error notifying tournament start: {str(e)}')
            return False

    def notify_tournament_end(self, tournament_id: int) -> bool:
        """Powiadamia o zakończeniu turnieju"""
        try:
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return False

            users = User.query.filter_by(is_active=True).all()
            
            title = "Zakończenie turnieju"
            message = f"Turniej {tournament.name} został zakończony"
            
            for user in users:
                self.create_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type='tournament_end',
                    related_id=tournament_id
                )
            return True
        except Exception as e:
            current_app.logger.error(f'Error notifying tournament end: {str(e)}')
            return False

    def clear_old_notifications(self, days: int = 30) -> bool:
        """Usuwa stare powiadomienia"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = Notification.query.filter(
                Notification.created_at < cutoff_date,
                Notification.is_read == True
            ).delete()

            log = SystemLog(
                type='info',
                user='system',
                action='clear_notifications',
                details=f'Usunięto {deleted} starych powiadomień'
            )
            self.add(log)
            self.commit()
            return True
        except Exception as e:
            current_app.logger.error(f'Error clearing old notifications: {str(e)}')
            return False 