from typing import Any, Optional, Dict, List, Callable
from datetime import datetime, timedelta
import json
from flask import current_app
from functools import wraps
import time

from models import SystemLog, Tournament, Team, Match, TournamentStanding
from services.base_service import BaseService
from services.config_service import ConfigService
from extensions import db

class CacheService(BaseService):
    _instance = None
    _cache: Dict[str, Any] = {}
    _cache_times: Dict[str, datetime] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            super().__init__()
            self.config_service = ConfigService()
            self.initialized = True

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Pobiera wartość z cache'u"""
        try:
            if key not in cls._cache or key not in cls._cache_times:
                return None

            # Sprawdź czy wartość nie wygasła
            if datetime.utcnow() > cls._cache_times[key]:
                cls.delete(key)
                return None

            return cls._cache[key]
        except Exception as e:
            current_app.logger.error(f'Error getting from cache: {str(e)}')
            return None

    @classmethod
    def set(cls, key: str, value: Any, expires_in: int = 300) -> bool:
        """Zapisuje wartość w cache'u"""
        try:
            cls._cache[key] = value
            cls._cache_times[key] = datetime.utcnow() + timedelta(seconds=expires_in)
            return True
        except Exception as e:
            current_app.logger.error(f'Error setting cache: {str(e)}')
            return False

    @classmethod
    def delete(cls, key: str) -> bool:
        """Usuwa wartość z cache'u"""
        try:
            if key in cls._cache:
                del cls._cache[key]
            if key in cls._cache_times:
                del cls._cache_times[key]
            return True
        except Exception as e:
            current_app.logger.error(f'Error deleting from cache: {str(e)}')
            return False

    @classmethod
    def clear(cls) -> bool:
        """Czyści cały cache"""
        try:
            cls._cache.clear()
            cls._cache_times.clear()
            return True
        except Exception as e:
            current_app.logger.error(f'Error clearing cache: {str(e)}')
            return False

    @classmethod
    def get_or_set(cls, key: str, callback: Callable, timeout: int = 300) -> Any:
        """Get from cache or set using callback if not found."""
        value = cls.get(key)
        if value is not None:
            return value
        
        try:
            value = callback()
            cls.set(key, value, timeout)
            return value
        except Exception as e:
            current_app.logger.error(f"Cache get_or_set error: {str(e)}")
            return callback()  # Fallback to direct call

    def get_stats(self) -> Dict:
        """Zwraca statystyki cache'u"""
        try:
            current_time = datetime.utcnow()
            active_keys = [k for k, t in self._cache_times.items() if t > current_time]
            expired_keys = [k for k, t in self._cache_times.items() if t <= current_time]

            return {
                'total_entries': len(self._cache),
                'active_entries': len(active_keys),
                'expired_entries': len(expired_keys),
                'memory_usage': self._estimate_memory_usage()
            }
        except Exception as e:
            current_app.logger.error(f'Error getting cache stats: {str(e)}')
            return {
                'total_entries': 0,
                'active_entries': 0,
                'expired_entries': 0,
                'memory_usage': 0
            }

    def _estimate_memory_usage(self) -> int:
        """Szacuje zużycie pamięci przez cache (w bajtach)"""
        try:
            total_size = 0
            for key, value in self._cache.items():
                # Rozmiar klucza
                total_size += len(key.encode('utf-8'))
                
                # Rozmiar wartości
                if isinstance(value, (str, bytes, bytearray)):
                    total_size += len(value)
                elif isinstance(value, (int, float)):
                    total_size += 8
                elif isinstance(value, (list, dict, tuple)):
                    total_size += len(json.dumps(value, default=str).encode('utf-8'))
                else:
                    # Dla innych typów szacujemy
                    total_size += 100

            return total_size
        except Exception as e:
            current_app.logger.error(f'Error estimating memory usage: {str(e)}')
            return 0

    def cleanup_expired(self) -> int:
        """Usuwa wygasłe wpisy z cache'u"""
        try:
            current_time = datetime.utcnow()
            expired_keys = [k for k, t in self._cache_times.items() if t <= current_time]
            
            for key in expired_keys:
                self.delete(key)

            return len(expired_keys)
        except Exception as e:
            current_app.logger.error(f'Error cleaning up cache: {str(e)}')
            return 0

    # Dekoratory do cache'owania
    @classmethod
    def cached(cls, key_prefix: str, expires_in: int = 300):
        """Dekorator do cache'owania wyników funkcji"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generuj klucz cache'u
                cache_key = f"{key_prefix}:{func.__name__}:"
                if args:
                    cache_key += ":".join(str(arg) for arg in args)
                if kwargs:
                    cache_key += ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

                # Sprawdź cache
                cached_value = cls.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Wykonaj funkcję i zapisz wynik
                result = func(*args, **kwargs)
                cls.set(cache_key, result, expires_in)
                return result
            return wrapper
        return decorator

    @classmethod
    def invalidate_pattern(cls, pattern: str) -> int:
        """Usuwa wszystkie wpisy z cache'u pasujące do wzorca"""
        try:
            keys_to_delete = [
                key for key in cls._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_delete:
                cls.delete(key)

            return len(keys_to_delete)
        except Exception as e:
            current_app.logger.error(f'Error invalidating cache pattern: {str(e)}')
            return 0

    @classmethod
    def get_keys(cls, pattern: Optional[str] = None) -> List[str]:
        """Zwraca listę kluczy w cache'u"""
        try:
            if pattern:
                return [key for key in cls._cache.keys() if pattern in key]
            return list(cls._cache.keys())
        except Exception as e:
            current_app.logger.error(f'Error getting cache keys: {str(e)}')
            return []

    def log_cache_operation(self, operation: str, details: str, 
                          user_email: str = 'system') -> None:
        """Loguje operację na cache'u"""
        try:
            log = SystemLog(
                type='info',
                user=user_email,
                action=f'cache_{operation}',
                details=details
            )
            self.add(log)
            self.commit()
        except Exception as e:
            current_app.logger.error(f'Error logging cache operation: {str(e)}')

    @classmethod
    def get_tournament_stats(cls, tournament_id: int, force_refresh: bool = False) -> Dict:
        """Get cached tournament statistics."""
        cache_key = f"tournament_stats:{tournament_id}"
        
        if force_refresh:
            cls.delete(cache_key)
        
        def calculate_stats():
            try:
                tournament = Tournament.query.get(tournament_id)
                if not tournament:
                    return {}
                
                teams = Team.query.filter_by(tournament_id=tournament_id).all()
                matches = Match.query.filter_by(tournament_id=tournament_id).all()
                
                stats = {
                    'total_teams': len(teams),
                    'total_matches': len(matches),
                    'completed_matches': len([m for m in matches if m.status == 'finished']),
                    'ongoing_matches': len([m for m in matches if m.status == 'ongoing']),
                    'planned_matches': len([m for m in matches if m.status == 'planned']),
                    'total_goals': sum((m.team1_score or 0) + (m.team2_score or 0) 
                                     for m in matches if m.status == 'finished'),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                return stats
            except Exception as e:
                current_app.logger.error(f"Error calculating tournament stats: {str(e)}")
                return {}
        
        return cls.get_or_set(cache_key, calculate_stats, timeout=600)  # 10 minutes
    
    @classmethod
    def get_team_standings(cls, tournament_id: int, force_refresh: bool = False) -> List[Dict]:
        """Get cached team standings for tournament."""
        cache_key = f"team_standings:{tournament_id}"
        
        if force_refresh:
            cls.delete(cache_key)
        
        def calculate_standings():
            try:
                teams = Team.query.filter_by(tournament_id=tournament_id).all()
                matches = Match.query.filter_by(tournament_id=tournament_id, status='finished').all()
                
                standings = []
                for team in teams:
                    stats = {
                        'team_id': team.id,
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
                    
                    for match in matches:
                        if match.team1_id == team.id:
                            stats['matches_played'] += 1
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
                                
                        elif match.team2_id == team.id:
                            stats['matches_played'] += 1
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
                    
                    stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
                    standings.append(stats)
                
                # Sort by points, then goal difference, then goals for
                standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
                
                return standings
            except Exception as e:
                current_app.logger.error(f"Error calculating team standings: {str(e)}")
                return []
        
        return cls.get_or_set(cache_key, calculate_standings, timeout=300)  # 5 minutes
    
    @classmethod
    def invalidate_tournament_cache(cls, tournament_id: int) -> None:
        """Invalidate all cache entries related to a tournament."""
        try:
            keys_to_delete = []
            for key in cls._cache.keys():
                if f":{tournament_id}" in key or f"tournament:{tournament_id}" in key:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                cls.delete(key)
                
        except Exception as e:
            current_app.logger.error(f"Error invalidating tournament cache: {str(e)}")
    
    @classmethod
    def get_cache_stats(cls) -> Dict:
        """Get cache statistics."""
        try:
            now = datetime.utcnow()
            expired_count = sum(1 for exp_time in cls._cache_times.values() if now > exp_time)
            
            return {
                'total_keys': len(cls._cache),
                'expired_keys': expired_count,
                'active_keys': len(cls._cache) - expired_count,
                'memory_usage_mb': sum(len(str(v)) for v in cls._cache.values()) / 1024 / 1024
            }
        except Exception as e:
            current_app.logger.error(f"Error getting cache stats: {str(e)}")
            return {} 