from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from flask import current_app
from sqlalchemy.orm import joinedload

from models import SystemConfig, SystemLog
from services.base_service import BaseService

class ConfigService(BaseService):
    # Stałe konfiguracyjne
    DEFAULT_CONFIG = {
        'tournament': {
            'default_match_length': 20,  # minuty
            'default_break_length': 5,   # minuty
            'min_teams': 2,
            'max_teams': 16,
            'points_for_win': 3,
            'points_for_draw': 1,
            'points_for_loss': 0
        },
        'match': {
            'allow_score_edit_after_end': False,
            'auto_end_after_length': True,
            'show_timer': True,
            'allow_pause': True
        },
        'notifications': {
            'enable_email_notifications': False,
            'notify_match_start': True,
            'notify_match_end': True,
            'notify_tournament_start': True,
            'notify_tournament_end': True
        },
        'system': {
            'maintenance_mode': False,
            'debug_mode': False,
            'log_retention_days': 90,
            'notification_retention_days': 30,
            'max_export_rows': 10000,
            'session_timeout': 3600  # sekundy
        },
        'ui': {
            'items_per_page': 20,
            'refresh_interval': 30,  # sekundy
            'show_team_logos': True,
            'enable_dark_mode': False,
            'language': 'pl'
        }
    }

    def get_config(self, section: Optional[str] = None) -> Dict:
        """Pobiera konfigurację systemu"""
        try:
            if section and section not in self.DEFAULT_CONFIG:
                return {}

            configs = SystemConfig.query.all()
            current_config = {}

            # Załaduj zapisane wartości
            for config in configs:
                sections = config.key.split('.')
                if len(sections) != 2:
                    continue

                section_name, key = sections
                if section_name not in current_config:
                    current_config[section_name] = {}
                current_config[section_name][key] = config.value

            # Uzupełnij brakujące wartości domyślnymi
            for section_name, section_config in self.DEFAULT_CONFIG.items():
                if section and section != section_name:
                    continue
                if section_name not in current_config:
                    current_config[section_name] = {}
                for key, default_value in section_config.items():
                    if key not in current_config[section_name]:
                        current_config[section_name][key] = default_value

            return current_config if not section else current_config[section]
        except Exception as e:
            current_app.logger.error(f'Error getting config: {str(e)}')
            return self.DEFAULT_CONFIG if not section else self.DEFAULT_CONFIG.get(section, {})

    def get_config_value(self, section: str, key: str) -> Any:
        """Pobiera pojedynczą wartość konfiguracji"""
        try:
            config = SystemConfig.query.filter_by(key=f'{section}.{key}').first()
            if config:
                return config.value
            return self.DEFAULT_CONFIG.get(section, {}).get(key)
        except Exception as e:
            current_app.logger.error(f'Error getting config value: {str(e)}')
            return self.DEFAULT_CONFIG.get(section, {}).get(key)

    def set_config_value(self, section: str, key: str, value: Any, 
                        user_email: str) -> Tuple[bool, str]:
        """Ustawia pojedynczą wartość konfiguracji"""
        try:
            if section not in self.DEFAULT_CONFIG or key not in self.DEFAULT_CONFIG[section]:
                return False, "Nieprawidłowy klucz konfiguracji"

            # Sprawdź typ wartości
            default_value = self.DEFAULT_CONFIG[section][key]
            if not isinstance(value, type(default_value)):
                return False, f"Nieprawidłowy typ wartości. Oczekiwano: {type(default_value)}"

            config_key = f'{section}.{key}'
            config = SystemConfig.query.filter_by(key=config_key).first()
            
            if config:
                old_value = config.value
                config.value = value
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    key=config_key,
                    value=value,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.add(config)

            log = SystemLog(
                type='info',
                user=user_email,
                action='update_config',
                details=f'Zmieniono konfigurację {config_key} z {old_value if "old_value" in locals() else "domyślnej"} na {value}'
            )
            self.add(log)
            self.commit()

            return True, "Konfiguracja została zaktualizowana"
        except Exception as e:
            current_app.logger.error(f'Error setting config value: {str(e)}')
            return False, "Wystąpił błąd podczas aktualizacji konfiguracji"

    def update_section(self, section: str, values: Dict[str, Any], 
                      user_email: str) -> Tuple[bool, str]:
        """Aktualizuje całą sekcję konfiguracji"""
        try:
            if section not in self.DEFAULT_CONFIG:
                return False, "Nieprawidłowa sekcja konfiguracji"

            success = True
            message = "Konfiguracja została zaktualizowana"

            for key, value in values.items():
                if key in self.DEFAULT_CONFIG[section]:
                    result, _ = self.set_config_value(section, key, value, user_email)
                    if not result:
                        success = False
                        message = "Niektóre wartości nie zostały zaktualizowane"

            return success, message
        except Exception as e:
            current_app.logger.error(f'Error updating config section: {str(e)}')
            return False, "Wystąpił błąd podczas aktualizacji konfiguracji"

    def reset_to_default(self, section: Optional[str] = None, 
                        user_email: str = 'system') -> Tuple[bool, str]:
        """Resetuje konfigurację do wartości domyślnych"""
        try:
            if section and section not in self.DEFAULT_CONFIG:
                return False, "Nieprawidłowa sekcja konfiguracji"

            query = SystemConfig.query
            if section:
                query = query.filter(SystemConfig.key.like(f'{section}.%'))
            
            deleted = query.delete()

            log = SystemLog(
                type='warning',
                user=user_email,
                action='reset_config',
                details=f'Zresetowano konfigurację{f" sekcji {section}" if section else ""} do wartości domyślnych'
            )
            self.add(log)
            self.commit()

            return True, f"Zresetowano {deleted} ustawień do wartości domyślnych"
        except Exception as e:
            current_app.logger.error(f'Error resetting config: {str(e)}')
            return False, "Wystąpił błąd podczas resetowania konfiguracji"

    def validate_config(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Sprawdza poprawność całej konfiguracji"""
        try:
            errors = {}
            current_config = self.get_config()

            for section, section_config in self.DEFAULT_CONFIG.items():
                section_errors = []
                
                # Sprawdź czy wszystkie wymagane klucze istnieją
                for key, default_value in section_config.items():
                    if section not in current_config or key not in current_config[section]:
                        section_errors.append(f'Brak wymaganego klucza: {key}')
                        continue

                    current_value = current_config[section][key]
                    
                    # Sprawdź typ wartości
                    if not isinstance(current_value, type(default_value)):
                        section_errors.append(
                            f'Nieprawidłowy typ dla {key}: {type(current_value)}, '
                            f'oczekiwano: {type(default_value)}'
                        )

                    # Dodatkowe walidacje dla konkretnych wartości
                    if section == 'tournament':
                        if key == 'min_teams' and current_value < 2:
                            section_errors.append('min_teams nie może być mniejsze niż 2')
                        elif key == 'max_teams' and current_value < current_config[section]['min_teams']:
                            section_errors.append('max_teams nie może być mniejsze niż min_teams')

                    elif section == 'system':
                        if key.endswith('_days') and current_value < 1:
                            section_errors.append(f'{key} musi być większe niż 0')
                        elif key == 'session_timeout' and current_value < 300:
                            section_errors.append('session_timeout nie może być krótszy niż 5 minut')

                if section_errors:
                    errors[section] = section_errors

            return len(errors) == 0, errors
        except Exception as e:
            current_app.logger.error(f'Error validating config: {str(e)}')
            return False, {'system': ['Wystąpił błąd podczas walidacji konfiguracji']} 