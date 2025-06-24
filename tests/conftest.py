import pytest
from app import create_app
from extensions import db
from models import User
from extensions import bcrypt

@pytest.fixture
def app():
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        # Tworzenie testowego admina
        if not User.query.filter_by(email='test@admin.com').first():
            admin = User(
                email='test@admin.com',
                password=bcrypt.generate_password_hash('test123').decode('utf-8'),
                role='admin',
                is_primary_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    yield app
    
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def auth_client(client):
    from flask import url_for
    
    # Get CSRF token first
    with client.session_transaction() as sess:
        sess['_csrf_token'] = 'test_token'
    
    client.post(url_for('auth.login', role='admin'), data={
        'email': 'test@admin.com',
        'password': 'test123',
        'remember_me': False,
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    return client

@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User.query.filter_by(email='test@admin.com').first()
        return admin 