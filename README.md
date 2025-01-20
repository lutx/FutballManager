# Football Team Management System

System do zarządzania turniejami piłkarskimi dla młodzieży.

## Funkcjonalności

- Zarządzanie rocznikami
- Organizacja turniejów
- Zarządzanie drużynami
- Śledzenie wyników meczów w czasie rzeczywistym
- Panel administratora
- Panel rodzica
- System powiadomień
- Statystyki i raporty

## Wymagania techniczne

- Python 3.8+
- Flask
- SQLAlchemy
- Flask-Login
- Flask-WTF
- Flask-Migrate
- Flask-Bcrypt
- Flask-Limiter

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/lutx/FutballManager.git
cd FutballManager
```

2. Stwórz i aktywuj wirtualne środowisko:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

4. Skonfiguruj zmienne środowiskowe:
```bash
cp .env.example .env
# Edytuj plik .env i ustaw wymagane zmienne
```

5. Zainicjalizuj bazę danych:
```bash
flask db upgrade
```

6. Uruchom aplikację:
```bash
python app.py
```

## Struktura projektu

```
football_team_management/
├── app.py                 # Główny plik aplikacji
├── config.py             # Konfiguracja
├── models.py             # Modele bazy danych
├── extensions.py         # Rozszerzenia Flask
├── decorators.py         # Dekoratory
├── requirements.txt      # Zależności
├── static/              # Pliki statyczne
├── templates/           # Szablony HTML
├── blueprints/          # Blueprinty Flask
├── services/            # Serwisy
├── forms/               # Formularze
└── migrations/          # Migracje bazy danych
```

## Rozwój

1. Stwórz nową gałąź dla swojej funkcjonalności:
```bash
git checkout -b feature/nazwa-funkcjonalnosci
```

2. Wprowadź zmiany i przetestuj

3. Wyślij pull request

## Licencja

Ten projekt jest licencjonowany na warunkach MIT License 