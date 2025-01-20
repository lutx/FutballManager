from app import create_app
from extensions import db
import importlib
import os

def run_migrations():
    app = create_app()
    
    with app.app_context():
        # Lista plików migracji do wykonania
        migration_files = [
            'migrations.add_field_number'
        ]
        
        try:
            for migration in migration_files:
                # Importuj moduł migracji
                migration_module = importlib.import_module(migration)
                
                # Wykonaj migrację
                print(f'Wykonywanie migracji: {migration}')
                migration_module.upgrade()
                print(f'Migracja {migration} zakończona pomyślnie')
                
            print('Wszystkie migracje zostały wykonane pomyślnie')
            
        except Exception as e:
            print(f'Błąd podczas wykonywania migracji: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    run_migrations() 