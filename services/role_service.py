from typing import List, Optional, Tuple
from flask import current_app
from sqlalchemy.orm import joinedload

from models import Role, User, SystemLog, Permission
from services.base_service import BaseService

class RoleService(BaseService):
    def get_role(self, role_id: int) -> Optional[Role]:
        """Pobiera rolę po ID"""
        return Role.query.options(
            joinedload('permissions')
        ).get(role_id)

    def get_all_roles(self) -> List[Role]:
        """Pobiera wszystkie role"""
        return Role.query.options(
            joinedload('permissions')
        ).all()

    def create_role(self, name: str, description: str, 
                   permission_ids: List[int], admin_email: str) -> Tuple[bool, str]:
        """Tworzy nową rolę z wybranymi uprawnieniami"""
        try:
            if not name:
                return False, "Nazwa roli jest wymagana"

            existing_role = Role.query.filter_by(name=name).first()
            if existing_role:
                return False, "Rola o takiej nazwie już istnieje"

            # Sprawdź czy wszystkie uprawnienia istnieją
            permissions = Permission.query.filter(
                Permission.id.in_(permission_ids)
            ).all()
            if len(permissions) != len(permission_ids):
                return False, "Niektóre uprawnienia nie istnieją"

            new_role = Role(
                name=name,
                description=description,
                permissions=permissions
            )
            self.add(new_role)

            log = SystemLog(
                type='info',
                user=admin_email,
                action='create_role',
                details=f'Utworzono nową rolę: {name}'
            )
            self.add(log)
            self.commit()

            return True, "Rola została utworzona"
        except Exception as e:
            current_app.logger.error(f'Error creating role: {str(e)}')
            return False, "Wystąpił błąd podczas tworzenia roli"

    def update_role(self, role_id: int, name: str, description: str, 
                   permission_ids: List[int], admin_email: str) -> Tuple[bool, str]:
        """Aktualizuje istniejącą rolę"""
        try:
            role = self.get_role(role_id)
            if not role:
                return False, "Rola nie istnieje"

            if not name:
                return False, "Nazwa roli jest wymagana"

            existing_role = Role.query.filter(
                Role.name == name,
                Role.id != role_id
            ).first()
            if existing_role:
                return False, "Rola o takiej nazwie już istnieje"

            # Sprawdź czy wszystkie uprawnienia istnieją
            permissions = Permission.query.filter(
                Permission.id.in_(permission_ids)
            ).all()
            if len(permissions) != len(permission_ids):
                return False, "Niektóre uprawnienia nie istnieją"

            role.name = name
            role.description = description
            role.permissions = permissions

            log = SystemLog(
                type='info',
                user=admin_email,
                action='update_role',
                details=f'Zaktualizowano rolę: {name}'
            )
            self.add(log)
            self.commit()

            return True, "Rola została zaktualizowana"
        except Exception as e:
            current_app.logger.error(f'Error updating role: {str(e)}')
            return False, "Wystąpił błąd podczas aktualizacji roli"

    def delete_role(self, role_id: int, admin_email: str) -> Tuple[bool, str]:
        """Usuwa rolę jeśli nie jest przypisana do żadnego użytkownika"""
        try:
            role = self.get_role(role_id)
            if not role:
                return False, "Rola nie istnieje"

            # Sprawdź czy rola jest używana
            users_with_role = User.query.filter_by(role_id=role_id).count()
            if users_with_role > 0:
                return False, "Nie można usunąć roli, która jest przypisana do użytkowników"

            role_name = role.name
            self.delete(role)

            log = SystemLog(
                type='warning',
                user=admin_email,
                action='delete_role',
                details=f'Usunięto rolę: {role_name}'
            )
            self.add(log)
            self.commit()

            return True, "Rola została usunięta"
        except Exception as e:
            current_app.logger.error(f'Error deleting role: {str(e)}')
            return False, "Wystąpił błąd podczas usuwania roli"

    def get_role_permissions(self, role_id: int) -> List[Permission]:
        """Pobiera wszystkie uprawnienia przypisane do roli"""
        try:
            role = self.get_role(role_id)
            return role.permissions if role else []
        except Exception as e:
            current_app.logger.error(f'Error getting role permissions: {str(e)}')
            return []

    def get_all_permissions(self) -> List[Permission]:
        """Pobiera wszystkie dostępne uprawnienia"""
        try:
            return Permission.query.all()
        except Exception as e:
            current_app.logger.error(f'Error getting permissions: {str(e)}')
            return []

    def has_permission(self, role_id: int, permission_name: str) -> bool:
        """Sprawdza czy rola ma określone uprawnienie"""
        try:
            role = self.get_role(role_id)
            if not role:
                return False
            return any(p.name == permission_name for p in role.permissions)
        except Exception as e:
            current_app.logger.error(f'Error checking permission: {str(e)}')
            return False 