from app import app
from extensions import db

with app.app_context():
    db.engine.execute('ALTER TABLE match ADD COLUMN is_timer_paused BOOLEAN DEFAULT FALSE;')
    print("Column added successfully!") 