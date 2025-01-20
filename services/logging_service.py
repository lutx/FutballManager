import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import desc
from models import SystemLog, db
from flask import current_app
import msvcrt
import time

class SafeRotatingFileHandler(RotatingFileHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_file = f"{self.baseFilename}.lock"

    def acquire_lock(self):
        """Bezpieczne uzyskanie blokady pliku dla Windows."""
        for _ in range(5):  # 5 prób
            try:
                if os.path.exists(self.lock_file):
                    # Jeśli plik blokady istnieje, sprawdź czy nie jest przestarzały
                    if time.time() - os.path.getmtime(self.lock_file) > 10:  # 10 sekund
                        try:
                            os.remove(self.lock_file)
                        except:
                            pass
                    else:
                        time.sleep(0.1)
                        continue

                # Próba utworzenia pliku blokady
                lock_file = open(self.lock_file, 'wb')
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    return lock_file
                except:
                    lock_file.close()
                    try:
                        os.remove(self.lock_file)
                    except:
                        pass
            except:
                pass
            time.sleep(0.1)
        return None

    def release_lock(self, lock_file):
        """Zwolnienie blokady pliku dla Windows."""
        if lock_file:
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass
            lock_file.close()
            try:
                os.remove(self.lock_file)
            except:
                pass

    def doRollover(self):
        """Bezpieczna rotacja plików logów."""
        lock_file = self.acquire_lock()
        if not lock_file:
            return  # Jeśli nie można uzyskać blokady, pomijamy rotację

        try:
            super().doRollover()
        finally:
            self.release_lock(lock_file)

class LoggingService:
    @staticmethod
    def setup_logging(app):
        """Konfiguracja systemu logowania z obsługą błędów."""
        try:
            # Upewnij się, że katalog logs istnieje
            if not os.path.exists('logs'):
                os.makedirs('logs', exist_ok=True)

            # Usuń stare handlery
            for handler in app.logger.handlers[:]:
                app.logger.removeHandler(handler)

            # Konfiguracja nowego handlera z bezpieczną rotacją
            file_handler = SafeRotatingFileHandler(
                'logs/app.log',
                maxBytes=10485760,  # 10MB
                backupCount=10,
                encoding='utf-8',
                delay=True
            )

            # Konfiguracja formatowania
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)

            # Dodaj handler do loggera aplikacji
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)

            # Dodaj handler konsoli w trybie debug
            if app.debug:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                app.logger.addHandler(console_handler)

            app.logger.info('System logowania został zainicjalizowany')

        except Exception as e:
            print(f"BŁĄD: Nie można skonfigurować systemu logowania: {str(e)}")
            # Fallback do podstawowego logowania
            logging.basicConfig(level=logging.INFO)

    @staticmethod
    def add_log(type: str, user: str, action: str, details: Optional[str] = None) -> Optional[SystemLog]:
        """Bezpieczne dodawanie logów z obsługą błędów."""
        try:
            log = SystemLog(
                type=type,
                user=user,
                action=action,
                details=details,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(log)
            db.session.commit()

            # Logowanie do pliku
            message = f"{action}: {details}" if details else action
            if type == 'error':
                current_app.logger.error(message)
            else:
                current_app.logger.info(message)

            return log

        except Exception as e:
            error_msg = f"Błąd podczas dodawania logu: {str(e)}"
            print(error_msg)  # Fallback logging
            try:
                db.session.rollback()
                current_app.logger.error(error_msg)
            except:
                pass
            return None

    @staticmethod
    def get_logs(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        log_type: Optional[str] = None,
        user: Optional[str] = None,
        action: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> tuple[List[SystemLog], int]:
        """Pobieranie logów z obsługą błędów i paginacją."""
        try:
            query = SystemLog.query

            if start_date:
                query = query.filter(SystemLog.timestamp >= start_date)
            if end_date:
                query = query.filter(SystemLog.timestamp <= end_date)
            if log_type:
                query = query.filter(SystemLog.type == log_type)
            if user:
                query = query.filter(SystemLog.user == user)
            if action:
                query = query.filter(SystemLog.action == action)

            total = query.count()
            logs = query.order_by(desc(SystemLog.timestamp))\
                       .offset((page - 1) * per_page)\
                       .limit(per_page)\
                       .all()

            return logs, total

        except Exception as e:
            error_msg = f"Błąd podczas pobierania logów: {str(e)}"
            current_app.logger.error(error_msg)
            return [], 0

    @staticmethod
    def get_log_summary(days: int = 7) -> Dict:
        """Generuje podsumowanie logów z ostatnich X dni."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            logs = SystemLog.query.filter(SystemLog.timestamp >= start_date).all()

            summary = {
                'total_logs': len(logs),
                'by_type': {},
                'by_action': {},
                'by_user': {},
                'period': {
                    'start': start_date,
                    'end': datetime.utcnow()
                }
            }

            for log in logs:
                # Liczenie według typu
                summary['by_type'][log.type] = summary['by_type'].get(log.type, 0) + 1
                # Liczenie według akcji
                summary['by_action'][log.action] = summary['by_action'].get(log.action, 0) + 1
                # Liczenie według użytkownika
                summary['by_user'][log.user] = summary['by_user'].get(log.user, 0) + 1

            return summary
        except Exception as e:
            current_app.logger.error(f'Błąd podczas generowania podsumowania logów: {str(e)}')
            raise

    @staticmethod
    def clear_old_logs(days: int = 30) -> bool:
        """Bezpieczne czyszczenie starych logów."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = SystemLog.query.filter(SystemLog.timestamp < cutoff_date).delete()
            db.session.commit()
            current_app.logger.info(f"Usunięto {deleted} starych logów")
            return True

        except Exception as e:
            error_msg = f"Błąd podczas czyszczenia starych logów: {str(e)}"
            current_app.logger.error(error_msg)
            db.session.rollback()
            return False

    @staticmethod
    def get_user_activity(user: str, days: int = 7) -> List[SystemLog]:
        """Pobiera aktywność konkretnego użytkownika z ostatnich X dni."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            logs = SystemLog.query.filter(
                SystemLog.user == user,
                SystemLog.timestamp >= start_date
            ).order_by(desc(SystemLog.timestamp)).all()
            return logs
        except Exception as e:
            current_app.logger.error(f'Błąd podczas pobierania aktywności użytkownika: {str(e)}')
            raise

    @staticmethod
    def get_recent_logs(limit=100):
        """Pobiera ostatnie logi z systemu."""
        try:
            return SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        except Exception as e:
            current_app.logger.error(f'Błąd podczas pobierania logów: {str(e)}')
            return [] 