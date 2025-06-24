import pytest
from flask import session, url_for

def test_login_page(client):
    """Test strony logowania"""
    response = client.get(url_for('auth.login'))
    assert response.status_code == 200
    assert 'Wybierz rolę' in response.get_data(as_text=True)

def test_successful_admin_login(client):
    """Test udanego logowania administratora"""
    response = client.post(url_for('auth.login', role='admin'), data={
        'email': 'test@admin.com',
        'password': 'test123',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Panel Administratora' in response.get_data(as_text=True)

def test_failed_login(client):
    """Test nieudanego logowania"""
    response = client.post(url_for('auth.login', role='admin'), data={
        'email': 'wrong@email.com',
        'password': 'wrongpass',
        'remember_me': False
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Nieprawidłowy email lub hasło' in response.get_data(as_text=True)

def test_logout(auth_client):
    """Test wylogowania"""
    response = auth_client.get(url_for('auth.logout'), follow_redirects=True)
    assert response.status_code == 200
    assert 'Zostałeś wylogowany' in response.get_data(as_text=True)

def test_login_required(client):
    """Test wymagania logowania dla chronionych stron"""
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert 'Zaloguj' in response.get_data(as_text=True)

def test_admin_access(auth_client):
    """Test dostępu do panelu admina"""
    response = auth_client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Panel Administratora' in response.data

def test_invalid_access(client):
    """Test dostępu do nieistniejącej strony"""
    response = client.get('/nonexistent', follow_redirects=True)
    assert response.status_code == 404

def test_csrf_protection(client):
    """Test ochrony CSRF"""
    response = client.post('/login', data={
        'email': 'test@admin.com',
        'password': 'test123'
    })
    assert response.status_code == 200
    assert b'CSRF' in response.data

def test_remember_me(client):
    """Test funkcji 'zapamiętaj mnie'"""
    with client.session_transaction() as sess:
        sess['_csrf_token'] = 'test_token'
    
    response = client.post(url_for('auth.login', role='admin'), data={
        'email': 'test@admin.com',
        'password': 'test123',
        'remember_me': True,
        'csrf_token': 'test_token'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        assert sess.permanent == True 