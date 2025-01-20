from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateTimeField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError, Email, EqualTo
from datetime import datetime

class EmptyForm(FlaskForm):
    submit = SubmitField('Potwierdź')

class YearForm(FlaskForm):
    year = IntegerField('Rocznik', validators=[
        DataRequired(message='To pole jest wymagane.'),
        NumberRange(min=1900, max=datetime.now().year, message='Wprowadź poprawny rok.')
    ])
    submit = SubmitField('Dodaj rocznik')

class TournamentForm(FlaskForm):
    name = StringField('Nazwa turnieju', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Length(min=3, max=100, message='Nazwa musi mieć od 3 do 100 znaków.')
    ])
    address = StringField('Adres', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Length(min=3, max=200, message='Adres musi mieć od 3 do 200 znaków.')
    ])
    number_of_fields = IntegerField('Liczba boisk', validators=[
        DataRequired(message='To pole jest wymagane.'),
        NumberRange(min=1, max=10, message='Liczba boisk musi być między 1 a 10.')
    ])
    match_length = IntegerField('Długość meczu (minuty)', validators=[
        DataRequired(message='To pole jest wymagane.'),
        NumberRange(min=5, max=90, message='Długość meczu musi być między 5 a 90 minut.')
    ])
    break_length = IntegerField('Długość przerwy (minuty)', validators=[
        DataRequired(message='To pole jest wymagane.'),
        NumberRange(min=1, max=30, message='Długość przerwy musi być między 1 a 30 minut.')
    ])
    submit = SubmitField('Dodaj turniej')

class TeamForm(FlaskForm):
    name = StringField('Nazwa drużyny', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Length(min=3, max=100, message='Nazwa musi mieć od 3 do 100 znaków.')
    ])
    submit = SubmitField('Dodaj drużynę')

class MatchForm(FlaskForm):
    team1_id = SelectField('Drużyna 1', coerce=int, validators=[
        DataRequired(message='To pole jest wymagane.')
    ])
    team2_id = SelectField('Drużyna 2', coerce=int, validators=[
        DataRequired(message='To pole jest wymagane.')
    ])
    start_time = DateTimeField('Czas rozpoczęcia', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message='To pole jest wymagane.')
    ])
    field_number = SelectField('Numer boiska', coerce=int, validators=[
        DataRequired(message='To pole jest wymagane.')
    ])
    submit = SubmitField('Dodaj mecz')
    
    def validate_team2_id(self, field):
        if field.data == self.team1_id.data:
            raise ValidationError('Drużyny muszą być różne.')

class AdminForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Email(message='Wprowadź poprawny adres email.')
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków.')
    ])
    confirm_password = PasswordField('Powtórz hasło', validators=[
        DataRequired(message='To pole jest wymagane.'),
        EqualTo('password', message='Hasła muszą być takie same.')
    ])
    submit = SubmitField('Dodaj administratora') 