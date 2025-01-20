import pytest
from models import User
from extensions import bcrypt

def test_new_user():
    """Test tworzenia nowego użytkownika"""
    user = User(
        email='test@test.com',
        password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        role='admin'
    )
    assert user.email == 'test@test.com'
    assert user.role == 'admin'
    assert user.is_primary_admin == False
    assert bcrypt.check_password_hash(user.password, 'test123')

def test_user_password_hashing():
    """Test hashowania hasła użytkownika"""
    password = 'test123'
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    assert bcrypt.check_password_hash(hashed, password)
    assert not bcrypt.check_password_hash(hashed, 'wrong_password')

def test_user_roles():
    """Test ról użytkownika"""
    admin = User(
        email='admin@test.com',
        password='test123',
        role='admin',
        is_primary_admin=True
    )
    assert admin.role == 'admin'
    assert admin.is_primary_admin == True

def test_user_authentication(app):
    """Test autentykacji użytkownika"""
    with app.app_context():
        # Tworzenie użytkownika
        password = 'test123'
        user = User(
            email='auth@test.com',
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='admin'
        )
        assert user.is_authenticated
        assert user.is_active
        assert not user.is_anonymous
        assert str(user.get_id()) == str(user.id)

def test_user_unique_email(app):
    """Test unikalności adresu email"""
    with app.app_context():
        # Pierwszy użytkownik
        user1 = User(
            email='unique@test.com',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
            role='admin'
        )
        from extensions import db
        db.session.add(user1)
        db.session.commit()

        # Próba utworzenia drugiego użytkownika z tym samym emailem
        with pytest.raises(Exception):
            user2 = User(
                email='unique@test.com',
                password=bcrypt.generate_password_hash('test123').decode('utf-8'),
                role='admin'
            )
            db.session.add(user2)
            db.session.commit() 