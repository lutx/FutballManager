from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Email(message='Wprowadź poprawny adres email.')
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(message='To pole jest wymagane.'),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków.')
    ])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj') 