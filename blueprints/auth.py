from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, SystemSettings
from extensions import db, bcrypt
from forms.auth import LoginForm
from services.logging_service import LoggingService

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
@bp.route('/login/<role>', methods=['GET', 'POST'])
def login(role=None):
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('parent.select_year'))
            
    form = LoginForm()
    logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
    logo_path = logo_setting.value if logo_setting else None

    if role == 'admin':
        if form.validate_on_submit():
            current_app.logger.info(f"Login attempt for email: {form.email.data}")
            
            user = User.query.filter_by(email=form.email.data).first()
            current_app.logger.info(f"User found: {user is not None}")
            
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                current_app.logger.info("Password check passed")
                if user.role != 'admin':
                    current_app.logger.error("User is not an admin")
                    flash('Brak uprawnień administratora', 'danger')
                    return redirect(url_for('auth.login'))
                    
                login_user(user, remember=form.remember_me.data)
                if form.remember_me.data:
                    session.permanent = True
                current_app.logger.info("User logged in successfully")
                
                LoggingService.add_log(
                    type='info',
                    user=user.email,
                    action='login',
                    details='Administrator zalogował się'
                )
                
                return redirect(url_for('admin.dashboard'))
            else:
                current_app.logger.error("Invalid email or password")
                flash('Nieprawidłowy email lub hasło', 'danger')
        return render_template('auth/login.html', role_selected='admin', form=form, logo_path=logo_path)
    
    elif role == 'parent':
        # Dla roli rodzica nie wymagamy logowania, tylko ustawiamy sesję
        session['role'] = 'parent'
        return redirect(url_for('parent.select_year'))
    
    return render_template('auth/login.html', role_selected=None, form=form, logo_path=logo_path)

@bp.route('/logout')
def logout():
    try:
        if current_user.is_authenticated:
            LoggingService.add_log(
                type='info',
                user=current_user.email,
                action='logout',
                details='Użytkownik wylogował się'
            )
            logout_user()
        
        if 'role' in session:
            session.pop('role')
        flash('Zostałeś wylogowany', 'success')
    except Exception as e:
        current_app.logger.error(f'Błąd podczas wylogowywania: {str(e)}')
        flash('Wystąpił błąd podczas wylogowywania', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html') 