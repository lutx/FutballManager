import logging
from logging.handlers import RotatingFileHandler
import os
import fcntl
import platform
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import desc
from models import SystemLog, db
from flask import current_app
import time

class SafeRotatingFileHandler(RotatingFileHandler):
    """Cross-platform safe rotating file handler."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_file = f"{self.baseFilename}.lock"

    def acquire_lock(self):
        """Safely acquire file lock for cross-platform support."""
        for _ in range(5):  # 5 attempts
            try:
                if os.path.exists(self.lock_file):
                    # If lock file exists, check if it's stale
                    if time.time() - os.path.getmtime(self.lock_file) > 10:  # 10 seconds
                        try:
                            os.remove(self.lock_file)
                        except:
                            pass
                    else:
                        time.sleep(0.1)
                        continue

                # Try to create lock file
                lock_file = open(self.lock_file, 'wb')
                try:
                    if platform.system() != 'Windows':
                        # Unix/Linux file locking
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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
        """Release file lock for cross-platform support."""
        if lock_file:
            try:
                if platform.system() != 'Windows':
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except:
                pass
            lock_file.close()
            try:
                os.remove(self.lock_file)
            except:
                pass

    def doRollover(self):
        """Safe log file rotation."""
        lock_file = self.acquire_lock()
        if not lock_file:
            return  # Skip rotation if can't acquire lock

        try:
            super().doRollover()
        finally:
            self.release_lock(lock_file)

class LoggingService:
    @staticmethod
    def setup_logging(app):
        """Configure logging system with error handling."""
        try:
            # Ensure logs directory exists
            if not os.path.exists('logs'):
                os.makedirs('logs', exist_ok=True)

            # Remove old handlers
            for handler in app.logger.handlers[:]:
                app.logger.removeHandler(handler)

            # Configure new handler with safe rotation
            file_handler = SafeRotatingFileHandler(
                'logs/app.log',
                maxBytes=10485760,  # 10MB
                backupCount=10,
                encoding='utf-8',
                delay=True
            )

            # Configure formatting
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)

            # Add handler to app logger
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)

            # Add console handler in debug mode
            if app.debug:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                app.logger.addHandler(console_handler)

            app.logger.info('Logging system initialized successfully')

        except Exception as e:
            print(f"ERROR: Cannot configure logging system: {str(e)}")
            # Fallback to basic logging
            logging.basicConfig(level=logging.INFO)

    @staticmethod
    def add_log(type: str, user: str, action: str, details: Optional[str] = None) -> Optional[SystemLog]:
        """Safely add logs with error handling."""
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

            # Log to file
            message = f"{action}: {details}" if details else action
            if type == 'error':
                current_app.logger.error(message)
            else:
                current_app.logger.info(message)

            return log

        except Exception as e:
            error_msg = f"Error adding log: {str(e)}"
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
        """Get logs with error handling and pagination."""
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
            error_msg = f"Error retrieving logs: {str(e)}"
            current_app.logger.error(error_msg)
            return [], 0

    @staticmethod
    def get_log_summary(days: int = 7) -> Dict:
        """Generate log summary for the last X days."""
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
                # Count by type
                summary['by_type'][log.type] = summary['by_type'].get(log.type, 0) + 1
                # Count by action
                summary['by_action'][log.action] = summary['by_action'].get(log.action, 0) + 1
                # Count by user
                summary['by_user'][log.user] = summary['by_user'].get(log.user, 0) + 1

            return summary
        except Exception as e:
            current_app.logger.error(f'Error generating log summary: {str(e)}')
            raise

    @staticmethod
    def clear_old_logs(days: int = 30) -> bool:
        """Safely clear old logs."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = SystemLog.query.filter(SystemLog.timestamp < cutoff_date).delete()
            db.session.commit()
            current_app.logger.info(f"Deleted {deleted} old logs")
            return True

        except Exception as e:
            error_msg = f"Error clearing old logs: {str(e)}"
            current_app.logger.error(error_msg)
            db.session.rollback()
            return False

    @staticmethod
    def get_user_activity(user: str, days: int = 7) -> List[SystemLog]:
        """Get specific user activity from the last X days."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            logs = SystemLog.query.filter(
                SystemLog.user == user,
                SystemLog.timestamp >= start_date
            ).order_by(desc(SystemLog.timestamp)).all()
            return logs
        except Exception as e:
            current_app.logger.error(f'Error retrieving user activity: {str(e)}')
            raise

    @staticmethod
    def get_recent_logs(limit=100):
        """Get recent logs from system."""
        try:
            return SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        except Exception as e:
            current_app.logger.error(f'Error retrieving logs: {str(e)}')
            return [] 