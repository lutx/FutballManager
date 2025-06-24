from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')
    is_primary_admin = db.Column(db.Boolean, nullable=False, default=False)

class Year(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    tournaments = db.relationship('Tournament', backref='year', lazy=True)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year_id = db.Column(db.Integer, db.ForeignKey('year.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='planned')
    date = db.Column(db.Date)
    address = db.Column(db.String(200))
    start_time = db.Column(db.DateTime)
    number_of_fields = db.Column(db.Integer, default=1)
    match_length = db.Column(db.Integer, default=20)
    break_length = db.Column(db.Integer, default=5)
    teams = db.relationship('Team', backref='tournament', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='tournament', lazy=True, cascade='all, delete-orphan')

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    matches_team1 = db.relationship('Match', backref='team1', lazy=True, foreign_keys='Match.team1_id')
    matches_team2 = db.relationship('Match', backref='team2', lazy=True, foreign_keys='Match.team2_id')

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team1_score = db.Column(db.Integer)
    team2_score = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)
    field_number = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), nullable=False, default='planned')
    is_timer_paused = db.Column(db.Boolean, default=True)
    elapsed_time = db.Column(db.Integer, default=0)

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(20), nullable=False)
    user = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)

# Alias for backward compatibility
SystemConfig = SystemSettings

class TournamentStanding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    goals_for = db.Column(db.Integer, default=0)
    goals_against = db.Column(db.Integer, default=0)
    goal_difference = db.Column(db.Integer, default=0)

    tournament = db.relationship('Tournament', backref='standings')
    team = db.relationship('Team', backref='standings')

    def update_from_match(self, match):
        if match.status != 'finished':
            return

        is_team1 = self.team_id == match.team1_id
        own_score = match.team1_score if is_team1 else match.team2_score
        opponent_score = match.team2_score if is_team1 else match.team1_score

        self.matches_played += 1
        self.goals_for += own_score
        self.goals_against += opponent_score
        self.goal_difference = self.goals_for - self.goals_against

        if own_score > opponent_score:
            self.wins += 1
            self.points += 3
        elif own_score == opponent_score:
            self.draws += 1
            self.points += 1
        else:
            self.losses += 1

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    related_tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)
    related_match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)

    user = db.relationship('User', backref='notifications')
    tournament = db.relationship('Tournament', backref='notifications')
    match = db.relationship('Match', backref='notifications')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def __init__(self, type, data=None):
        self.type = type
        self.data = data or {}
        self.status = 'pending'
    
    def complete(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def fail(self, error_message):
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message 