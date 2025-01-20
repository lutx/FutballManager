from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import json
from flask import current_app
from functools import wraps

from models import SystemLog
from services.base_service import BaseService
from services.config_service import ConfigService

class CacheService(BaseService):
    def __init__(self):
        super().__init__()
        self.config_service = ConfigService()
        self._cache = {}
        self._cache_times = {}

    def get(self, key: str) -> Optional[Any]:
        """Pobiera wartość z cache'u"""
        try:
            if key not in self._cache or key not in self._cache_times:
                return None

            # Sprawdź czy wartość nie wygasła
            if datetime.utcnow() > self._cache_times[key]:
                self.delete(key)
                return None

            return self._cache[key]
        except Exception as e:
            current_app.logger.error(f'Error getting from cache: {str(e)}')
            return None

    def set(self, key: str, value: Any, expires_in: int = 300) -> bool:
        """Zapisuje wartość w cache'u"""
        try:
            self._cache[key] = value
            self._cache_times[key] = datetime.utcnow() + timedelta(seconds=expires_in)
            return True
        except Exception as e:
            current_app.logger.error(f'Error setting cache: {str(e)}')
            return False

    def delete(self, key: str) -> bool:
        """Usuwa wartość z cache'u"""
        try:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_times:
                del self._cache_times[key]
            return True
        except Exception as e:
            current_app.logger.error(f'Error deleting from cache: {str(e)}')
            return False

    def clear(self) -> bool:
        """Czyści cały cache"""
        try:
            self._cache.clear()
            self._cache_times.clear()
            return True
        except Exception as e:
            current_app.logger.error(f'Error clearing cache: {str(e)}')
            return False

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
                    total_size += len(json.dumps(value).encode('utf-8'))
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
    def cached(self, key_prefix: str, expires_in: int = 300):
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
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Wykonaj funkcję i zapisz wynik
                result = func(*args, **kwargs)
                self.set(cache_key, result, expires_in)
                return result
            return wrapper
        return decorator

    def invalidate_pattern(self, pattern: str) -> int:
        """Usuwa wszystkie wpisy z cache'u pasujące do wzorca"""
        try:
            keys_to_delete = [
                key for key in self._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_delete:
                self.delete(key)

            return len(keys_to_delete)
        except Exception as e:
            current_app.logger.error(f'Error invalidating cache pattern: {str(e)}')
            return 0

    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Zwraca listę kluczy w cache'u"""
        try:
            if pattern:
                return [key for key in self._cache.keys() if pattern in key]
            return list(self._cache.keys())
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