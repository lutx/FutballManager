"""Add performance indexes to database tables

This migration adds indexes to improve query performance for commonly used queries.
"""

from flask import current_app
from extensions import db
from sqlalchemy import text

def upgrade():
    """Add performance indexes to the database."""
    try:
        # Match table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_tournament_id ON match(tournament_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_status ON match(status)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_start_time ON match(start_time)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_team1_id ON match(team1_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_team2_id ON match(team2_id)'))
        
        # Tournament table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_year_id ON tournament(year_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_status ON tournament(status)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_date ON tournament(date)'))
        
        # Team table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_team_tournament_id ON team(tournament_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_team_name ON team(name)'))
        
        # SystemLog table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_log_timestamp ON system_log(timestamp)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_log_type ON system_log(type)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_log_user ON system_log(user)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_log_action ON system_log(action)'))
        
        # User table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_user_email ON user(email)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_user_role ON user(role)'))
        
        # TournamentStanding table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_standing_tournament_id ON tournament_standing(tournament_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_standing_team_id ON tournament_standing(team_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_standing_points ON tournament_standing(points)'))
        
        # Notification table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_notification_user_id ON notification(user_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_notification_timestamp ON notification(timestamp)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_notification_is_read ON notification(is_read)'))
        
        # Task table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_task_type ON task(type)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_task_status ON task(status)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_task_created_at ON task(created_at)'))
        
        # SystemSettings table indexes
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_settings_key ON system_settings(key)'))
        
        # Composite indexes for common queries
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_tournament_status ON match(tournament_id, status)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_match_teams ON match(team1_id, team2_id)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_tournament_year_status ON tournament(year_id, status)'))
        db.engine.execute(text('CREATE INDEX IF NOT EXISTS ix_system_log_type_timestamp ON system_log(type, timestamp)'))
        
        current_app.logger.info('Performance indexes added successfully')
        
    except Exception as e:
        current_app.logger.error(f'Error adding performance indexes: {str(e)}')
        raise

def downgrade():
    """Remove performance indexes from the database."""
    try:
        # Drop all indexes created in upgrade
        indexes_to_drop = [
            'ix_match_tournament_id',
            'ix_match_status',
            'ix_match_start_time',
            'ix_match_team1_id',
            'ix_match_team2_id',
            'ix_tournament_year_id',
            'ix_tournament_status',
            'ix_tournament_date',
            'ix_team_tournament_id',
            'ix_team_name',
            'ix_system_log_timestamp',
            'ix_system_log_type',
            'ix_system_log_user',
            'ix_system_log_action',
            'ix_user_email',
            'ix_user_role',
            'ix_tournament_standing_tournament_id',
            'ix_tournament_standing_team_id',
            'ix_tournament_standing_points',
            'ix_notification_user_id',
            'ix_notification_timestamp',
            'ix_notification_is_read',
            'ix_task_type',
            'ix_task_status',
            'ix_task_created_at',
            'ix_system_settings_key',
            'ix_match_tournament_status',
            'ix_match_teams',
            'ix_tournament_year_status',
            'ix_system_log_type_timestamp'
        ]
        
        for index_name in indexes_to_drop:
            try:
                db.engine.execute(text(f'DROP INDEX IF EXISTS {index_name}'))
            except Exception as e:
                current_app.logger.warning(f'Could not drop index {index_name}: {str(e)}')
        
        current_app.logger.info('Performance indexes removed successfully')
        
    except Exception as e:
        current_app.logger.error(f'Error removing performance indexes: {str(e)}')
        raise

if __name__ == '__main__':
    # Allow running this migration directly
    from app import create_app
    
    app = create_app()
    with app.app_context():
        print("Adding performance indexes...")
        upgrade()
        print("Performance indexes added successfully!")