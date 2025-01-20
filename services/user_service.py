from typing import Optional, Tuple, List
from flask import current_app
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload

from models import User, SystemLog, Role
from services.base_service import BaseService

class UserService(BaseService):
    def get_user(self, user_id: int) -> Optional[User]:
        return User.query.options(
            joinedload('role')
        ).get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[User]]:
        try:
            user = self.get_user_by_email(email)
            if not user:
                return False, "Nieprawidłowy email lub hasło", None

            if not check_password_hash(user.password, password):
                return False, "Nieprawidłowy email lub hasło", None

            if not user.is_active:
                return False, "Konto jest nieaktywne", None

            login_user(user)

            log = SystemLog(
                type='info',
                user=email,
                action='login',
                details=f'Użytkownik {email} zalogował się'
            )
            self.add(log)
            self.commit()

            return True, "Zalogowano pomyślnie", user
        except Exception as e:
            current_app.logger.error(f'Error authenticating user: {str(e)}')
            return False, "Wystąpił błąd podczas logowania", None

    def logout_user_service(self, user_email: str) -> Tuple[bool, str]:
        try:
            logout_user()
            
            log = SystemLog(
                type='info',
                user=user_email,
                action='logout',
                details=f'Użytkownik {user_email} wylogował się'
            )
            self.add(log)
            self.commit()

            return True, "Wylogowano pomyślnie"
        except Exception as e:
            current_app.logger.error(f'Error logging out user: {str(e)}')
            return False, "Wystąpił błąd podczas wylogowywania"

    def create_user(self, email: str, password: str, role_id: int, 
                   first_name: str, last_name: str, admin_email: str) -> Tuple[bool, str]:
        try:
            if not email or not password or not role_id:
                return False, "Wszystkie pola są wymagane"

            existing_user = self.get_user_by_email(email)
            if existing_user:
                return False, "Użytkownik o takim emailu już istnieje"

            role = Role.query.get(role_id)
            if not role:
                return False, "Wybrana rola nie istnieje"

            hashed_password = generate_password_hash(password)
            new_user = User(
                email=email,
                password=hashed_password,
                role_id=role_id,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            self.add(new_user)

            log = SystemLog(
                type='info',
                user=admin_email,
                action='create_user',
                details=f'Utworzono nowego użytkownika: {email} z rolą {role.name}'
            )
            self.add(log)
            self.commit()

            return True, "Użytkownik został utworzony"
        except Exception as e:
            current_app.logger.error(f'Error creating user: {str(e)}')
            return False, "Wystąpił błąd podczas tworzenia użytkownika"

    def update_user(self, user_id: int, email: str, role_id: int, 
                   first_name: str, last_name: str, is_active: bool, 
                   admin_email: str) -> Tuple[bool, str]:
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Użytkownik nie istnieje"

            if not email or not role_id:
                return False, "Email i rola są wymagane"

            existing_user = User.query.filter(
                User.email == email,
                User.id != user_id
            ).first()
            if existing_user:
                return False, "Użytkownik o takim emailu już istnieje"

            role = Role.query.get(role_id)
            if not role:
                return False, "Wybrana rola nie istnieje"

            user.email = email
            user.role_id = role_id
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active

            log = SystemLog(
                type='info',
                user=admin_email,
                action='update_user',
                details=f'Zaktualizowano użytkownika: {email}'
            )
            self.add(log)
            self.commit()

            return True, "Użytkownik został zaktualizowany"
        except Exception as e:
            current_app.logger.error(f'Error updating user: {str(e)}')
            return False, "Wystąpił błąd podczas aktualizacji użytkownika"

    def change_password(self, user_id: int, current_password: str, 
                       new_password: str) -> Tuple[bool, str]:
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Użytkownik nie istnieje"

            if not check_password_hash(user.password, current_password):
                return False, "Nieprawidłowe obecne hasło"

            user.password = generate_password_hash(new_password)

            log = SystemLog(
                type='warning',
                user=user.email,
                action='change_password',
                details=f'Użytkownik {user.email} zmienił hasło'
            )
            self.add(log)
            self.commit()

            return True, "Hasło zostało zmienione"
        except Exception as e:
            current_app.logger.error(f'Error changing password: {str(e)}')
            return False, "Wystąpił błąd podczas zmiany hasła"

    def reset_password(self, user_id: int, new_password: str, admin_email: str) -> Tuple[bool, str]:
        try:
            user = self.get_user(user_id)
            if not user:
                return False, "Użytkownik nie istnieje"

            user.password = generate_password_hash(new_password)

            log = SystemLog(
                type='warning',
                user=admin_email,
                action='reset_password',
                details=f'Administrator {admin_email} zresetował hasło użytkownika {user.email}'
            )
            self.add(log)
            self.commit()

            return True, "Hasło zostało zresetowane"
        except Exception as e:
            current_app.logger.error(f'Error resetting password: {str(e)}')
            return False, "Wystąpił błąd podczas resetowania hasła" 