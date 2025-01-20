from app import create_app, db

def clear_db():
    """Czyści wszystkie tabele w bazie danych"""
    app = create_app()
    
    with app.app_context():
        try:
            db.drop_all()
            db.create_all()
            print("Baza danych została wyczyszczona.")
        except Exception as e:
            print(f"Wystąpił błąd podczas czyszczenia bazy danych: {e}")

if __name__ == '__main__':
    if input("Czy na pewno chcesz wyczyścić bazę danych? (tak/nie): ").lower() == 'tak':
        clear_db()
    else:
        print("Operacja anulowana.") 