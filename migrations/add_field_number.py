from extensions import db
from models import Match
import sqlite3

def upgrade():
    """Dodaje kolumnę field_number do tabeli match w sposób bezpieczny dla SQLite."""
    try:
        # 1. Utwórz tymczasową tabelę z nową strukturą
        db.session.execute('''
            CREATE TABLE match_new (
                id INTEGER PRIMARY KEY,
                tournament_id INTEGER NOT NULL,
                team1_id INTEGER NOT NULL,
                team2_id INTEGER NOT NULL,
                team1_score INTEGER,
                team2_score INTEGER,
                start_time DATETIME,
                field_number INTEGER DEFAULT 1,
                status VARCHAR(20) NOT NULL DEFAULT 'planned',
                is_timer_paused BOOLEAN DEFAULT 1,
                elapsed_time INTEGER DEFAULT 0,
                FOREIGN KEY(tournament_id) REFERENCES tournament(id),
                FOREIGN KEY(team1_id) REFERENCES team(id),
                FOREIGN KEY(team2_id) REFERENCES team(id)
            )
        ''')

        # 2. Skopiuj dane ze starej tabeli do nowej
        db.session.execute('''
            INSERT INTO match_new (
                id, tournament_id, team1_id, team2_id, team1_score, team2_score,
                start_time, status, is_timer_paused, elapsed_time
            )
            SELECT id, tournament_id, team1_id, team2_id, team1_score, team2_score,
                   start_time, status, is_timer_paused, elapsed_time
            FROM "match"
        ''')

        # 3. Usuń starą tabelę
        db.session.execute('DROP TABLE "match"')

        # 4. Zmień nazwę nowej tabeli na właściwą
        db.session.execute('ALTER TABLE match_new RENAME TO "match"')

        # 5. Dodaj indeksy
        db.session.execute('CREATE INDEX ix_match_tournament_id ON "match" (tournament_id)')
        db.session.execute('CREATE INDEX ix_match_team1_id ON "match" (team1_id)')
        db.session.execute('CREATE INDEX ix_match_team2_id ON "match" (team2_id)')
        db.session.execute('CREATE INDEX ix_match_status ON "match" (status)')

        db.session.commit()
        print("Migracja zakończona sukcesem")
        
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas migracji: {str(e)}")
        raise

def downgrade():
    """Usuwa kolumnę field_number z tabeli match."""
    try:
        # 1. Utwórz tymczasową tabelę bez kolumny field_number
        db.session.execute('''
            CREATE TABLE match_new (
                id INTEGER PRIMARY KEY,
                tournament_id INTEGER NOT NULL,
                team1_id INTEGER NOT NULL,
                team2_id INTEGER NOT NULL,
                team1_score INTEGER,
                team2_score INTEGER,
                start_time DATETIME,
                status VARCHAR(20) NOT NULL DEFAULT 'planned',
                is_timer_paused BOOLEAN DEFAULT 1,
                elapsed_time INTEGER DEFAULT 0,
                FOREIGN KEY(tournament_id) REFERENCES tournament(id),
                FOREIGN KEY(team1_id) REFERENCES team(id),
                FOREIGN KEY(team2_id) REFERENCES team(id)
            )
        ''')

        # 2. Skopiuj dane bez kolumny field_number
        db.session.execute('''
            INSERT INTO match_new (
                id, tournament_id, team1_id, team2_id, team1_score, team2_score,
                start_time, status, is_timer_paused, elapsed_time
            )
            SELECT id, tournament_id, team1_id, team2_id, team1_score, team2_score,
                   start_time, status, is_timer_paused, elapsed_time
            FROM "match"
        ''')

        # 3. Usuń starą tabelę
        db.session.execute('DROP TABLE "match"')

        # 4. Zmień nazwę nowej tabeli na właściwą
        db.session.execute('ALTER TABLE match_new RENAME TO "match"')

        # 5. Odtwórz indeksy
        db.session.execute('CREATE INDEX ix_match_tournament_id ON "match" (tournament_id)')
        db.session.execute('CREATE INDEX ix_match_team1_id ON "match" (team1_id)')
        db.session.execute('CREATE INDEX ix_match_team2_id ON "match" (team2_id)')
        db.session.execute('CREATE INDEX ix_match_status ON "match" (status)')

        db.session.commit()
        print("Cofnięcie migracji zakończone sukcesem")
        
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas cofania migracji: {str(e)}")
        raise 