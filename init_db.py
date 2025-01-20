from extensions import db, bcrypt
from models import User, Year, Tournament, Team, Match, SystemLog, SystemSettings

def init_db(app):
    with app.app_context():
        # Usuń wszystkie tabele
        db.drop_all()
        # Utwórz wszystkie tabele
        db.create_all()
        
        # Utwórz głównego administratora
        admin = User(
            email='admin@admin.com',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin',
            is_primary_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        
        print("Baza danych została zainicjalizowana")
        print("Utworzono głównego administratora:")
        print("Email: admin@admin.com")
        print("Hasło: admin123")

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    init_db(app) 