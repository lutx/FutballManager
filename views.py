from flask import render_template, redirect, url_for, flash, request, session, abort, jsonify, Response, stream_with_context, current_app
from flask_login import login_required, current_user, logout_user
from flask_wtf import FlaskForm
from models import User, Year, Tournament, Team, Match, SystemLog, SystemSettings
from forms.auth import LoginForm
from extensions import db, bcrypt
import os
from werkzeug.utils import secure_filename
import datetime
from flask_wtf.csrf import CSRFProtect
import json
import queue
import threading
import time

# Global queues for updates
match_updates = queue.Queue()
tournament_updates = queue.Queue()

def init_views(app):
    # Import blueprints
    from blueprints.auth import bp as auth_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.parent import bp as parent_bp
    from blueprints.api import bp as api_bp
    from blueprints.main import bp as main_bp

    # Register blueprints with URL prefixes
    app.register_blueprint(main_bp)  # No prefix for main blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Template filters
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        return value.strftime(format)

    @app.route('/logout')
    def logout():
        try:
            was_authenticated = False
            
            if current_user.is_authenticated:
                # Dodaj log wylogowania dla admina
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='logout',
                    details='Wylogowanie z systemu'
                )
                db.session.add(log)
                db.session.commit()
                logout_user()
            
            # Wyczyść sesję rodzica jeśli istnieje
            if session.get('role'):
                session.clear()  # Czyścimy całą sesję
                
            # Wyświetl komunikat tylko raz
            if was_authenticated or session.get('role'):
                flash('Wylogowano pomyślnie', 'success')
            
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd wylogowania: {str(e)}')
            flash('Wystąpił błąd podczas wylogowania', 'danger')
            return redirect(url_for('auth.login'))

    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/login/<role>', methods=['GET', 'POST'])
    def login(role=None):
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                logout_user()
                flash('Nieprawidłowa rola użytkownika', 'danger')
                return redirect(url_for('login'))
            
        form = LoginForm()
        logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
        logo_path = logo_setting.value if logo_setting else None
        
        if role == 'admin':
            if request.method == 'POST':
                app.logger.info(f"Login attempt for email: {request.form.get('email')}")
                
                if not form.validate_on_submit():
                    app.logger.error(f"Form validation errors: {form.errors}")
                    return render_template('login.html', role_selected='admin', form=form, logo_path=logo_path)
                
                user = User.query.filter_by(email=form.email.data).first()
                app.logger.info(f"User found: {user is not None}")
                
                if user and bcrypt.check_password_hash(user.password, form.password.data):
                    app.logger.info("Password check passed")
                    if user.role != 'admin':
                        app.logger.error("User is not an admin")
                        flash('Brak uprawnień administratora', 'danger')
                        return redirect(url_for('login'))
                    login_user(user)
                    app.logger.info("User logged in successfully")
                    return redirect(url_for('admin_dashboard'))
                else:
                    app.logger.error("Invalid email or password")
                flash('Nieprawidłowy email lub hasło', 'danger')
            return render_template('login.html', role_selected='admin', form=form, logo_path=logo_path)
        elif role == 'parent':
            # For parent role, redirect directly to year selection
            return redirect(url_for('parent_select_year'))
        
        return render_template('auth/login.html', role_selected=None, form=form, logo_path=logo_path)

    @app.route('/parent/select-year')
    def parent_select_year():
        try:
            years = Year.query.order_by(Year.year.desc()).all()
            logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
            logo_path = logo_setting.value if logo_setting else None
            
            # Add tournament count for each year
            for year in years:
                year.tournaments_count = len(year.tournaments)
            
            return render_template('parent/select_year.html', 
                                years=years,
                                logo_path=logo_path)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania roczników: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('parent.select_year'))

    @app.route('/parent/years/<int:year_id>')
    def parent_dashboard(year_id):
        try:
            year = Year.query.get_or_404(year_id)
            tournaments = Tournament.query.filter_by(year_id=year_id).all()
            logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
            logo_path = logo_setting.value if logo_setting else None
            
            return render_template('parent/tournaments.html',
                                year=year,
                                tournaments=tournaments,
                                logo_path=logo_path)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania turniejów: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('parent.select_year'))

    @app.route('/parent/tournament/<int:tournament_id>')
    def parent_tournament_details(tournament_id):
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.start_time).all()
            teams = Team.query.filter_by(tournament_id=tournament_id).all()
            logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
            logo_path = logo_setting.value if logo_setting else None
            
            # Calculate team statistics
            team_stats = []
            for team in teams:
                stats = {
                    'team': team,
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'points': 0
                }
                
                for match in matches:
                    if match.status != 'finished':
                        continue
                    
                    if match.team1_id == team.id:
                        stats['goals_for'] += match.team1_score or 0
                        stats['goals_against'] += match.team2_score or 0
                        if match.team1_score > match.team2_score:
                            stats['wins'] += 1
                            stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            stats['draws'] += 1
                            stats['points'] += 1
                        else:
                            stats['losses'] += 1
                        stats['matches_played'] += 1
                    elif match.team2_id == team.id:
                        stats['goals_for'] += match.team2_score or 0
                        stats['goals_against'] += match.team1_score or 0
                        if match.team2_score > match.team1_score:
                            stats['wins'] += 1
                            stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            stats['draws'] += 1
                            stats['points'] += 1
                        else:
                            stats['losses'] += 1
                        stats['matches_played'] += 1
                
                team_stats.append(stats)
            
            # Sort teams by points
            team_stats.sort(key=lambda x: (-x['points'], -(x['goals_for'] - x['goals_against']), -x['goals_for']))
            
            return render_template('parent/tournament_details.html',
                                tournament=tournament,
                                matches=matches,
                                team_stats=team_stats,
                                logo_path=logo_path)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania szczegółów turnieju: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('parent.tournaments'))

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień do dostępu do panelu admina', 'danger')
            return redirect(url_for('auth.login'))
            
        try:
            stats = {
                'years_count': Year.query.count(),
                'tournaments_count': Tournament.query.count(),
                'teams_count': Team.query.count(),
                'active_matches': Match.query.filter_by(status='ongoing').count()
            }
            active_tournaments = Tournament.query.filter_by(status='ongoing').all()
            recent_matches = Match.query.order_by(Match.start_time.desc()).limit(5).all()
            form = EmptyForm()
            
            return render_template('admin/dashboard.html', 
                                stats=stats,
                                active_tournaments=active_tournaments,
                                recent_matches=recent_matches,
                                form=form)
        except SQLAlchemyError as e:
            app.logger.error(f'Błąd bazy danych: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('auth.login'))
        except Exception as e:
            app.logger.error(f'Nieoczekiwany błąd: {str(e)}')
            flash('Wystąpił nieoczekiwany błąd', 'danger')
            return redirect(url_for('auth.login'))

    @app.route('/admin/manage')
    @login_required
    def manage_admins():
        if not current_user.is_authenticated or not current_user.is_primary_admin:
            flash('Brak uprawnień do zarządzania administratorami', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            form = EmptyForm()  # Dodanie formularza dla tokenów CSRF
            admins = User.query.filter_by(role='admin').all()
            return render_template('admin/manage_admins.html', admins=admins, form=form)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania listy adminów: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('admin.dashboard'))

    @app.route('/admin/manage/add', methods=['POST'])
    @login_required
    def add_admin():
        if not current_user.is_primary_admin:
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Wszystkie pola są wymagane', 'danger')
                return redirect(url_for('admin.manage_admins'))
            
            if User.query.filter_by(email=email).first():
                flash('Administrator o tym adresie email już istnieje', 'danger')
                return redirect(url_for('admin.manage_admins'))
            
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_admin = User(
                email=email,
                password=hashed_password,
                role='admin',
                is_primary_admin=False
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            flash('Administrator został dodany pomyślnie', 'success')
            return redirect(url_for('admin.manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd podczas dodawania admina: {str(e)}')
            flash('Wystąpił błąd podczas dodawania administratora', 'danger')
            return redirect(url_for('admin.manage_admins'))

    @app.route('/admin/manage/delete/<int:admin_id>', methods=['POST'])
    @login_required
    def delete_admin(admin_id):
        if not current_user.is_primary_admin:
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            admin = User.query.get_or_404(admin_id)
            
            if admin.is_primary_admin:
                flash('Nie można usunąć głównego administratora', 'danger')
                return redirect(url_for('admin.manage_admins'))
            
            db.session.delete(admin)
            db.session.commit()
            
            flash('Administrator został usunięty', 'success')
            return redirect(url_for('admin.manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd podczas usuwania admina: {str(e)}')
            flash('Wystąpił błąd podczas usuwania administratora', 'danger')
            return redirect(url_for('admin.manage_admins'))

    @app.route('/admin/logo', methods=['GET', 'POST', 'DELETE'])
    @login_required
    def manage_logo():
        if not current_user.is_authenticated or not current_user.is_primary_admin:
            flash('Brak uprawnień do zarządzania logo', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            form = EmptyForm()  # Dodanie formularza dla CSRF
            
            if request.method == 'DELETE':
                if not form.validate():
                    return jsonify({'error': 'Invalid CSRF token'}), 400
                    
                logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
                if logo_setting and logo_setting.value:
                    try:
                        os.remove(os.path.join(app.root_path, 'static', logo_setting.value))
                    except:
                        pass
                    
                    logo_setting.value = None
                    db.session.commit()
                    return jsonify({'success': True})
                return jsonify({'error': 'No logo found'}), 404
            
            if request.method == 'POST':
                if not form.validate_on_submit():
                    flash('Błąd walidacji formularza', 'danger')
                    return redirect(request.url)
                    
                if 'logo' not in request.files:
                    flash('Nie wybrano pliku', 'danger')
                    return redirect(request.url)
                
                file = request.files['logo']
                if file.filename == '':
                    flash('Nie wybrano pliku', 'danger')
                    return redirect(request.url)
                
                if file and allowed_file(file.filename):
                    # Usuń stare logo jeśli istnieje
                    old_logo = SystemSettings.query.filter_by(key='logo_path').first()
                    if old_logo and old_logo.value:
                        try:
                            os.remove(os.path.join(app.root_path, 'static', old_logo.value))
                        except:
                            pass
                    
                    # Zapisz nowe logo
                    filename = secure_filename(f"logo_{int(datetime.datetime.now().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file.save(os.path.join(app.root_path, 'static', 'uploads', filename))
                    
                    # Zapisz ścieżkę do logo w ustawieniach
                    if old_logo:
                        old_logo.value = f'uploads/{filename}'
                    else:
                        setting = SystemSettings(key='logo_path', value=f'uploads/{filename}')
                        db.session.add(setting)
                    
                    db.session.commit()
                    flash('Logo zostało zaktualizowane', 'success')
                    return redirect(url_for('manage_logo'))
                else:
                    flash('Niedozwolony format pliku', 'danger')
            
            logo_path = SystemSettings.query.filter_by(key='logo_path').first()
            return render_template('admin/manage_logo.html', 
                                logo_path=logo_path.value if logo_path else None,
                                form=form)
            
        except Exception as e:
            app.logger.error(f'Błąd podczas zarządzania logo: {str(e)}')
            flash('Wystąpił błąd podczas zarządzania logo', 'danger')
            return redirect(url_for('admin.dashboard'))

    def allowed_file(filename):
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/admin/logs')
    @login_required
    def view_logs():
        if not current_user.is_authenticated or not current_user.is_primary_admin:
            flash('Brak uprawnień do przeglądania logów', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 20  # Zmniejszamy ilość logów na stronę dla lepszej czytelności
            
            # Filtrowanie
            log_type = request.args.get('type')
            action = request.args.get('action')
            user = request.args.get('user')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            query = SystemLog.query
            
            if log_type:
                query = query.filter_by(type=log_type)
            if action:
                query = query.filter_by(action=action)
            if user:
                query = query.filter(SystemLog.user.ilike(f'%{user}%'))
            if start_date:
                query = query.filter(SystemLog.timestamp >= datetime.datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                # Dodajemy 23:59:59 do daty końcowej, aby uwzględnić cały dzień
                end_datetime = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(SystemLog.timestamp <= end_datetime)
            
            # Sortowanie od najnowszych
            query = query.order_by(SystemLog.timestamp.desc())
            
            # Paginacja
            logs = query.paginate(page=page, per_page=per_page)
            
            return render_template('admin/logs.html', 
                                logs=logs)
            
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania logów: {str(e)}')
            flash('Wystąpił błąd podczas ładowania logów', 'danger')
            return redirect(url_for('admin.dashboard'))

    @app.route('/admin/logs/clear', methods=['POST'])
    @login_required
    def clear_logs():
        if not current_user.is_authenticated or not current_user.is_primary_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        try:
            # Usuń wszystkie logi starsze niż 30 dni
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
            SystemLog.query.filter(SystemLog.timestamp < thirty_days_ago).delete()
            db.session.commit()
            
            flash('Stare logi zostały usunięte', 'success')
            return redirect(url_for('view_logs'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd podczas czyszczenia logów: {str(e)}')
            flash('Wystąpił błąd podczas czyszczenia logów', 'danger')
            return redirect(url_for('view_logs'))

    @app.route('/admin/years', methods=['GET', 'POST'])
    @login_required
    def manage_years():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            form = EmptyForm()
            
            if request.method == 'POST' and form.validate_on_submit():
                year = request.form.get('year')
                if not year:
                    flash('Rok jest wymagany', 'danger')
                    return redirect(url_for('admin.manage_years'))
                
                if Year.query.filter_by(year=year).first():
                    flash('Ten rocznik już istnieje', 'danger')
                    return redirect(url_for('admin.manage_years'))
                
                new_year = Year(year=year)
                db.session.add(new_year)
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='add_year',
                    details=f'Dodano nowy rocznik: {year}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Rocznik został dodany', 'success')
                return redirect(url_for('admin.manage_years'))
            
            years = Year.query.order_by(Year.year.desc()).all()
            return render_template('admin/years.html', years=years, form=form)
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd podczas operacji na rocznikach: {str(e)}')
            flash('Wystąpił błąd podczas operacji', 'danger')
            return redirect(url_for('admin.dashboard'))

    @app.route('/admin/years/<int:year_id>/delete', methods=['POST'])
    @login_required
    def delete_year(year_id):
        if not current_user.is_authenticated or not current_user.is_primary_admin:
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('admin.manage_years'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                year = Year.query.get_or_404(year_id)
                
                # Usuń wszystkie powiązane turnieje
                for tournament in year.tournaments:
                    # Usuń wszystkie mecze w turnieju
                    Match.query.filter_by(tournament_id=tournament.id).delete()
                    # Usuń wszystkie drużyny w turnieju
                    Team.query.filter_by(tournament_id=tournament.id).delete()
                
                # Usuń turnieje
                Tournament.query.filter_by(year_id=year_id).delete()
                
                # Usuń rocznik
                db.session.delete(year)
                
                # Dodaj log
                log = SystemLog(
                    type='warning',
                    user=current_user.email,
                    action='delete_year',
                    details=f'Usunięto rocznik: {year.year}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Rocznik został usunięty', 'success')
                return redirect(url_for('admin.manage_years'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas usuwania rocznika: {str(e)}')
                flash('Wystąpił błąd podczas usuwania rocznika', 'danger')
                return redirect(url_for('admin.manage_years'))
        
        return redirect(url_for('admin.manage_years'))

    @app.route('/admin/years/<int:year_id>/tournaments')
    @login_required
    def year_tournaments(year_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        year = Year.query.get_or_404(year_id)
        tournaments = Tournament.query.filter_by(year_id=year_id).order_by(Tournament.id.desc()).all()
        form = EmptyForm()
        
        return render_template('admin/year_tournaments.html', 
                             year=year, 
                             tournaments=tournaments, 
                             form=form)

    @app.route('/admin/tournaments/add', methods=['POST'])
    @login_required
    def add_tournament():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                year_id = request.form.get('year_id')
                name = request.form.get('name')
                date = request.form.get('date')
                address = request.form.get('address')
                start_time = request.form.get('start_time')
                number_of_fields = request.form.get('number_of_fields', type=int, default=1)
                match_length = request.form.get('match_length', type=int, default=20)
                break_length = request.form.get('break_length', type=int, default=5)
                
                if not all([year_id, name]):
                    flash('Nazwa turnieju jest wymagana', 'danger')
                    return redirect(url_for('year_tournaments', year_id=year_id))
                
                # Konwertuj datę z formatu string na obiekt date
                tournament_date = None
                if date:
                    tournament_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
                
                # Konwertuj czas z formatu string na obiekt time
                tournament_time = None
                if start_time:
                    tournament_time = datetime.datetime.strptime(start_time, '%H:%M').time()
                
                new_tournament = Tournament(
                    name=name,
                    year_id=year_id,
                    status='planned',
                    date=tournament_date,
                    address=address,
                    start_time=tournament_time,
                    number_of_fields=number_of_fields,
                    match_length=match_length,
                    break_length=break_length
                )
                
                db.session.add(new_tournament)
                db.session.commit()
                
                app.logger.info(
                    f'Dodano nowy turniej: {name}',
                    extra={
                        'user': current_user.email,
                        'action': 'add_tournament'
                    }
                )
                
                flash(f'Turniej {name} został dodany pomyślnie', 'success')
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(
                    f'Błąd podczas dodawania turnieju: {str(e)}',
                    extra={
                        'user': current_user.email,
                        'action': 'add_tournament'
                    }
                )
                flash('Wystąpił błąd podczas dodawania turnieju', 'danger')
                
            return redirect(url_for('year_tournaments', year_id=year_id))
        
        flash('Nieprawidłowe żądanie', 'danger')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/tournaments/<int:tournament_id>/teams')
    @login_required
    def tournament_teams(tournament_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            teams = Team.query.filter_by(tournament_id=tournament_id).all()
            form = EmptyForm()
            return render_template('admin/tournament_teams.html', 
                                 tournament=tournament, 
                                 teams=teams,
                                 form=form)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania drużyn: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

    @app.route('/admin/teams/add', methods=['POST'])
    @login_required
    def add_team():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                tournament_id = request.form.get('tournament_id')
                name = request.form.get('name')
                
                if not name:
                    flash('Nazwa drużyny jest wymagana', 'danger')
                    return redirect(url_for('tournament_teams', tournament_id=tournament_id))
                
                tournament = Tournament.query.get_or_404(tournament_id)
                if tournament.status != 'planned':
                    flash('Można dodawać drużyny tylko do zaplanowanych turniejów', 'danger')
                    return redirect(url_for('tournament_teams', tournament_id=tournament_id))
                
                new_team = Team(
                    name=name,
                    tournament_id=tournament_id
                )
                db.session.add(new_team)
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='add_team',
                    details=f'Dodano nową drużynę: {name} do turnieju: {tournament.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Drużyna została dodana', 'success')
                return redirect(url_for('tournament_teams', tournament_id=tournament_id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas dodawania drużyny: {str(e)}')
                flash('Wystąpił błąd podczas dodawania drużyny', 'danger')
                return redirect(url_for('tournament_teams', tournament_id=tournament_id))
        
        return redirect(url_for('tournament_teams', tournament_id=request.form.get('tournament_id')))

    @app.route('/admin/teams/<int:team_id>/delete', methods=['POST'])
    @login_required
    def delete_team(team_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                team = Team.query.get_or_404(team_id)
                tournament = team.tournament
                
                if tournament.status != 'planned':
                    flash('Można usuwać drużyny tylko z zaplanowanych turniejów', 'danger')
                    return redirect(url_for('tournament_teams', tournament_id=tournament.id))
                
                # Usuń wszystkie mecze drużyny
                Match.query.filter(
                    (Match.team1_id == team_id) | (Match.team2_id == team_id)
                ).delete()
                
                # Usuń drużynę
                db.session.delete(team)
                
                # Dodaj log
                log = SystemLog(
                    type='warning',
                    user=current_user.email,
                    action='delete_team',
                    details=f'Usunięto drużynę: {team.name} z turnieju: {tournament.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Drużyna została usunięta', 'success')
                return redirect(url_for('tournament_teams', tournament_id=tournament.id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas usuwania drużyny: {str(e)}')
                flash('Wystąpił błąd podczas usuwania drużyny', 'danger')
                return redirect(url_for('tournament_teams', tournament_id=tournament.id))
        
        return redirect(url_for('tournament_teams', tournament_id=tournament.id))

    @app.route('/admin/tournaments/<int:tournament_id>/matches')
    @login_required
    def tournament_matches(tournament_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            # Sortowanie meczów po czasie rozpoczęcia
            matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.start_time.asc()).all()
            teams = Team.query.filter_by(tournament_id=tournament_id).all()
            form = EmptyForm()
            return render_template('admin/tournament_matches.html', 
                                 tournament=tournament,
                                 matches=matches,
                                 teams=teams,
                                 form=form)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania meczów: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

    @app.route('/admin/tournaments/<int:tournament_id>/results')
    @login_required
    def tournament_results(tournament_id):
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            matches = Match.query.filter_by(tournament_id=tournament_id).all()
            teams = Team.query.filter_by(tournament_id=tournament_id).all()
            
            # Oblicz statystyki dla każdej drużyny
            team_stats = []
            for team in teams:
                stats = {
                    'team': team,
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'points': 0
                }
                
                # Przeanalizuj wszystkie mecze drużyny
                for match in Match.query.filter(
                    (Match.team1_id == team.id) | (Match.team2_id == team.id),
                    Match.tournament_id == tournament_id,
                    Match.status == 'finished'
                ).all():
                    stats['matches_played'] += 1
                    
                    if match.team1_id == team.id:
                        stats['goals_for'] += match.team1_score or 0
                        stats['goals_against'] += match.team2_score or 0
                        if match.team1_score > match.team2_score:
                            stats['wins'] += 1
                            stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            stats['draws'] += 1
                            stats['points'] += 1
                        else:
                            stats['losses'] += 1
                    else:
                        stats['goals_for'] += match.team2_score or 0
                        stats['goals_against'] += match.team1_score or 0
                        if match.team2_score > match.team1_score:
                            stats['wins'] += 1
                            stats['points'] += 3
                        elif match.team1_score == match.team2_score:
                            stats['draws'] += 1
                            stats['points'] += 1
                        else:
                            stats['losses'] += 1
                
                team_stats.append(stats)
            
            # Posortuj drużyny według punktów
            team_stats.sort(key=lambda x: (-x['points'], -(x['goals_for'] - x['goals_against']), -x['goals_for']))
            
            return render_template('admin/tournament_results.html',
                                 tournament=tournament,
                                 team_stats=team_stats)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania wyników: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

    @app.route('/parent/tournaments')
    def parent_tournaments():
        try:
            tournaments = Tournament.query.filter_by(status='ongoing').all()
            logo_setting = SystemSettings.query.filter_by(key='logo_path').first()
            logo_path = logo_setting.value if logo_setting else None
            
            return render_template('parent/tournaments.html',
                                 tournaments=tournaments,
                                 logo_path=logo_path)
        except Exception as e:
            app.logger.error(f'Błąd podczas ładowania turniejów: {str(e)}')
            flash('Wystąpił błąd podczas ładowania danych', 'danger')
            return redirect(url_for('parent.select_year'))

    @app.route('/admin/tournaments/<int:tournament_id>/start', methods=['POST'])
    @login_required
    def start_tournament(tournament_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                tournament = Tournament.query.get_or_404(tournament_id)
                if tournament.status != 'planned':
                    flash('Turniej nie może zostać rozpoczęty', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                # Sprawdź czy są co najmniej 2 drużyny
                if len(tournament.teams) < 2:
                    flash('Potrzebne są co najmniej 2 drużyny aby rozpocząć turniej', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                # Sprawdź czy są dodane mecze
                matches = Match.query.filter_by(tournament_id=tournament_id).all()
                if not matches:
                    flash('Nie można rozpocząć turnieju bez dodanych meczów', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                # Sprawdź czy każda drużyna ma przypisany co najmniej jeden mecz
                teams_with_matches = set()
                for match in matches:
                    teams_with_matches.add(match.team1_id)
                    teams_with_matches.add(match.team2_id)
                
                if len(teams_with_matches) < len(tournament.teams):
                    flash('Każda drużyna musi mieć przypisany co najmniej jeden mecz', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                tournament.status = 'ongoing'
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='start_tournament',
                    details=f'Rozpoczęto turniej: {tournament.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                # Broadcast tournament update
                tournament_update = {
                    'tournament_id': tournament.id,
                    'tournament_status': tournament.status,
                    'matches': [],
                    'stats': []
                }
                match_updates.put(tournament_update)
                
                flash('Turniej został rozpoczęty', 'success')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas rozpoczynania turnieju: {str(e)}')
                flash('Wystąpił błąd podczas rozpoczynania turnieju', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
        
        return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))

    @app.route('/admin/tournaments/<int:tournament_id>/end', methods=['POST'])
    @login_required
    def end_tournament(tournament_id):
        app.logger.info(f'Attempting to end tournament {tournament_id}')
        if not current_user.is_authenticated or current_user.role != 'admin':
            app.logger.warning('User not authenticated or not admin')
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        app.logger.info('Form validation starting')
        if form.validate_on_submit():
            app.logger.info('Form validation successful')
            try:
                tournament = Tournament.query.get_or_404(tournament_id)
                app.logger.info(f'Found tournament: {tournament.name} with status: {tournament.status}')
                if tournament.status != 'ongoing':
                    app.logger.warning(f'Tournament status is {tournament.status}, cannot end')
                    flash('Turniej nie może zostać zakończony', 'danger')
                    return redirect(url_for('year_tournaments', year_id=tournament.year_id))
                
                tournament.status = 'finished'
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='end_tournament',
                    details=f'Zakończono turniej: {tournament.name}'
                )
                db.session.add(log)
                db.session.commit()
                app.logger.info('Tournament status updated and committed')
                
                # Broadcast tournament update
                tournament_update = {
                    'tournament_id': tournament.id,
                    'tournament_status': tournament.status,
                    'matches': [],
                    'stats': []
                }
                match_updates.put(tournament_update)
                app.logger.info('Tournament update broadcasted')
                
                flash('Turniej został zakończony', 'success')
                return redirect(url_for('year_tournaments', year_id=tournament.year_id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error ending tournament: {str(e)}')
                flash('Wystąpił błąd podczas kończenia turnieju', 'danger')
                return redirect(url_for('year_tournaments', year_id=tournament.year_id))
        else:
            app.logger.warning(f'Form validation failed. Errors: {form.errors}')
        
        return redirect(url_for('year_tournaments', year_id=tournament.year_id))

    @app.route('/admin/matches/add', methods=['POST'])
    @login_required
    def add_match():
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Brak uprawnień'}), 403
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                tournament_id = request.form.get('tournament_id') or request.args.get('tournament_id')
                team1_id = request.form.get('team1_id')
                team2_id = request.form.get('team2_id')
                start_time = request.form.get('start_time')
                
                if not all([tournament_id, team1_id, team2_id, start_time]):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': 'Wszystkie pola są wymagane'}), 400
                    flash('Wszystkie pola są wymagane', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=tournament_id))
                
                # Convert local time input to UTC for storage
                local_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
                utc_time = local_to_utc(local_time)
                
                # Sprawdź czy turniej istnieje i czy ma odpowiedni status
                tournament = Tournament.query.get_or_404(tournament_id)
                if tournament.status == 'finished':
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': 'Nie można dodawać meczów do zakończonego turnieju'}), 400
                    flash('Nie można dodawać meczów do zakończonego turnieju', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                elif tournament.status == 'ongoing' and not current_user.is_primary_admin:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': 'Tylko główny administrator może dodawać mecze do trwającego turnieju'}), 403
                    flash('Tylko główny administrator może dodawać mecze do trwającego turnieju', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))

                if team1_id == team2_id:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': 'Drużyny muszą być różne'}), 400
                    flash('Drużyny muszą być różne', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                # Sprawdź czy drużyny należą do tego turnieju
                team1 = Team.query.get_or_404(team1_id)
                team2 = Team.query.get_or_404(team2_id)
                if team1.tournament_id != int(tournament_id) or team2.tournament_id != int(tournament_id):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': 'Wybrane drużyny nie należą do tego turnieju'}), 400
                    flash('Wybrane drużyny nie należą do tego turnieju', 'danger')
                    return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
                
                new_match = Match(
                    tournament_id=tournament_id,
                    team1_id=team1_id,
                    team2_id=team2_id,
                    start_time=utc_time,
                    status='planned'
                )
                db.session.add(new_match)
                
                # Dodaj log
                log = SystemLog(
                    type='warning' if tournament.status == 'ongoing' else 'info',
                    user=current_user.email,
                    action='add_match',
                    details=f'{"[TURNIEJ W TRAKCIE] " if tournament.status == "ongoing" else ""}Dodano nowy mecz: {team1.name} vs {team2.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': 'Mecz został dodany',
                        'redirect': url_for('tournament_matches', tournament_id=tournament_id)
                    })
                flash('Mecz został dodany', 'success')
                return redirect(url_for('tournament_matches', tournament_id=tournament_id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Błąd podczas dodawania meczu: {str(e)}')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Wystąpił błąd podczas dodawania meczu'}), 500
                flash('Wystąpił błąd podczas dodawania meczu', 'danger')
                return redirect(url_for('tournament_matches', tournament_id=tournament_id))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Nieprawidłowe żądanie'}), 400
        return redirect(url_for('tournament_matches', tournament_id=request.form.get('tournament_id') or request.args.get('tournament_id')))

    def broadcast_match_update(match_id):
        """Broadcast match updates to all connected clients."""
        try:
            match = Match.query.get(match_id)
            if not match:
                app.logger.error(f'Match not found: {match_id}')
                return

            # Przygotuj dane do wysłania
            update_data = {
                'match_id': match_id,
                'team1_score': match.team1_score or 0,
                'team2_score': match.team2_score or 0,
                'status': match.status,
                'start_time': match.start_time.isoformat() if match.start_time else None,
                'match_length': match.tournament.match_length,
                'is_timer_paused': match.is_timer_paused,
                'elapsed_time': match.elapsed_time
            }

            # Dodaj do kolejki aktualizacji z timeoutem
            try:
                match_updates.put(update_data, timeout=1)
                app.logger.info(f'Match update broadcasted: {match_id}')
            except queue.Full:
                app.logger.warning(f'Update queue is full, skipping update for match: {match_id}')
            
        except Exception as e:
            app.logger.error(f'Error in broadcast_match_update: {str(e)}')

    @app.route('/admin/matches/<int:match_id>/start', methods=['POST'])
    @login_required
    def start_match(match_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                match = Match.query.get_or_404(match_id)
                tournament = match.tournament
                
                if tournament.status != 'ongoing':
                    flash('Można rozpoczynać mecze tylko w trwających turniejach', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=tournament.id))
                
                if match.status != 'planned':
                    flash('Ten mecz został już rozpoczęty lub zakończony', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=tournament.id))
                
                # Ustaw status i czas rozpoczęcia
                match.status = 'ongoing'
                match.start_time = datetime.datetime.now(datetime.timezone.utc)
                match.is_timer_paused = False
                match.elapsed_time = 0
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='start_match',
                    details=f'Rozpoczęto mecz: {match.team1.name} vs {match.team2.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                # Broadcast update
                broadcast_match_update(match_id)
                
                flash('Mecz został rozpoczęty', 'success')
                return redirect(url_for('tournament_matches', tournament_id=tournament.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error in start_match: {str(e)}')
                flash('Wystąpił błąd podczas rozpoczynania meczu', 'danger')
                return redirect(url_for('tournament_matches', tournament_id=tournament.id))
        
        return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))

    @app.route('/admin/matches/quick-update-score', methods=['POST'])
    @login_required
    def quick_update_match_score():
        """Update match score quickly."""
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Brak uprawnień'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Brak danych'}), 400
            
            try:
                match_id = int(data.get('match_id'))
                team_number = str(data.get('team_number'))
                action = str(data.get('action'))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Nieprawidłowy format danych'}), 400
            
            if not all([match_id, team_number in ['1', '2'], action in ['add', 'subtract']]):
                return jsonify({'success': False, 'message': 'Nieprawidłowe parametry'}), 400
            
            match = Match.query.get_or_404(match_id)
            
            if match.status != 'ongoing':
                return jsonify({'success': False, 'message': 'Mecz nie jest w trakcie'}), 400
            
            # Aktualizacja wyniku
            if team_number == '1':
                if action == 'add':
                    match.team1_score = (match.team1_score or 0) + 1
                elif action == 'subtract' and match.team1_score > 0:
                    match.team1_score = match.team1_score - 1
            elif team_number == '2':
                if action == 'add':
                    match.team2_score = (match.team2_score or 0) + 1
                elif action == 'subtract' and match.team2_score > 0:
                    match.team2_score = match.team2_score - 1
            
            try:
                db.session.commit()
                # Broadcast update
                broadcast_match_update(match_id)
                
                return jsonify({
                    'success': True,
                    'team1_score': match.team1_score or 0,
                    'team2_score': match.team2_score or 0,
                    'message': 'Wynik został zaktualizowany'
                })
            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f'Database error updating score: {str(e)}')
                return jsonify({
                    'success': False,
                    'message': 'Błąd bazy danych podczas aktualizacji wyniku'
                }), 500
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error updating score: {str(e)}')
            return jsonify({
                'success': False,
                'message': 'Wystąpił błąd podczas aktualizacji wyniku'
            }), 500

    @app.route('/admin/matches/<int:match_id>/toggle-timer', methods=['POST'])
    @login_required
    def toggle_match_timer(match_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Brak uprawnień'}), 403
        
        try:
            match = Match.query.get_or_404(match_id)
            if match.status != 'ongoing':
                return jsonify({'success': False, 'message': 'Można zatrzymać/wznowić timer tylko dla trwających meczów'}), 400
            
            # Toggle timer state
            match.is_timer_paused = not match.is_timer_paused
            
            # Calculate elapsed time regardless of pause state to ensure consistency
            if match.start_time:
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                start_time_utc = match.start_time.replace(tzinfo=datetime.timezone.utc)
                elapsed_seconds = int((now_utc - start_time_utc).total_seconds())
                
                # If pausing, store the current elapsed time
                if match.is_timer_paused:
                    match.elapsed_time = elapsed_seconds
                else:
                    # If resuming, adjust start_time to account for pause duration
                    if match.elapsed_time is not None:
                        pause_duration = elapsed_seconds - match.elapsed_time
                        match.start_time = match.start_time + datetime.timedelta(seconds=pause_duration)
                        match.elapsed_time = None
                
                # Add log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='toggle_timer',
                    details=f'{"Zatrzymano" if match.is_timer_paused else "Wznowiono"} timer meczu: {match.team1.name} vs {match.team2.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                # Broadcast update with current elapsed time
                broadcast_match_update(match_id)
                
                # Return new state
                return jsonify({
                    'success': True,
                    'is_paused': match.is_timer_paused,
                    'elapsed_time': match.elapsed_time if match.elapsed_time is not None else elapsed_seconds
                })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error in toggle_match_timer: {str(e)}')
            return jsonify({'success': False, 'message': 'Wystąpił błąd podczas aktualizacji timera'}), 500

    @app.route('/admin/tournaments/edit', methods=['POST'])
    @login_required
    def edit_tournament():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                tournament_id = request.form.get('tournament_id')
                name = request.form.get('name')
                date = request.form.get('date')
                address = request.form.get('address')
                start_time = request.form.get('start_time')
                number_of_fields = request.form.get('number_of_fields')
                match_length = request.form.get('match_length')
                break_length = request.form.get('break_length')
                
                if not all([tournament_id, name, date, address, start_time, number_of_fields, match_length, break_length]):
                    flash('Wszystkie pola są wymagane', 'danger')
                    return redirect(url_for('year_tournaments', year_id=request.form.get('year_id')))
                
                tournament = Tournament.query.get_or_404(tournament_id)
                
                # Sprawdź czy turniej może być edytowany
                if tournament.status != 'planned':
                    flash('Można edytować tylko zaplanowane turnieje', 'danger')
                    return redirect(url_for('year_tournaments', year_id=tournament.year_id))
                
                # Aktualizuj dane turnieju
                tournament.name = name
                tournament.date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
                tournament.address = address
                tournament.start_time = datetime.datetime.strptime(f"{date} {start_time}", '%Y-%m-%d %H:%M')
                tournament.number_of_fields = int(number_of_fields)
                tournament.match_length = int(match_length)
                tournament.break_length = int(break_length)
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='edit_tournament',
                    details=f'Zaktualizowano turniej: {tournament.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Turniej został zaktualizowany', 'success')
                return redirect(url_for('year_tournaments', year_id=tournament.year_id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas edycji turnieju: {str(e)}')
                flash('Wystąpił błąd podczas edycji turnieju', 'danger')
                return redirect(url_for('year_tournaments', year_id=request.form.get('year_id')))
        
        return redirect(url_for('year_tournaments', year_id=request.form.get('year_id')))

    @app.route('/admin/matches/<int:match_id>/end', methods=['POST'])
    @login_required
    def end_match(match_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                match = Match.query.get_or_404(match_id)
                tournament = match.tournament
                
                if match.status != 'ongoing':
                    flash('Można zakończyć tylko trwający mecz', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
                
                # Get tournament details
                match_length = tournament.match_length
                break_length = tournament.break_length
                
                # Get current time in local timezone and convert to UTC for storage
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                
                match.status = 'finished'
                
                # Get all subsequent matches on the same field that are planned
                subsequent_matches = Match.query.filter(
                    Match.tournament_id == tournament.id,
                    Match.field_number == match.field_number,
                    Match.status == 'planned'
                ).order_by(Match.start_time).all()
                
                # Update start times of subsequent matches based on actual end time
                next_start_time = now_utc + datetime.timedelta(minutes=break_length)
                for next_match in subsequent_matches:
                    next_match.start_time = next_start_time
                    next_start_time = next_start_time + datetime.timedelta(minutes=match_length + break_length)
                
                # Add log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='end_match',
                    details=f'Zakończono mecz: {match.team1.name} vs {match.team2.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                # Broadcast update to all clients
                broadcast_match_update(match_id)
                
                flash('Mecz został zakończony', 'success')
                return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas kończenia meczu: {str(e)}')
                flash('Wystąpił błąd podczas kończenia meczu', 'danger')
                return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
        
        return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))

    @app.route('/admin/matches/<int:match_id>/delete', methods=['POST'])
    @login_required
    def delete_match(match_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                match = Match.query.get_or_404(match_id)
                tournament_id = match.tournament_id
                
                if match.status != 'planned':
                    flash('Można usuwać tylko zaplanowane mecze', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=tournament_id))
                
                # Dodaj log przed usunięciem
                log = SystemLog(
                    type='warning',
                    user=current_user.email,
                    action='delete_match',
                    details=f'Usunięto mecz: {match.team1.name} vs {match.team2.name}'
                )
                db.session.add(log)
                
                # Usuń mecz
                db.session.delete(match)
                db.session.commit()
                
                flash('Mecz został usunięty', 'success')
                return redirect(url_for('tournament_matches', tournament_id=tournament_id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas usuwania meczu: {str(e)}')
                flash('Wystąpił błąd podczas usuwania meczu', 'danger')
                return redirect(url_for('tournament_matches', tournament_id=tournament_id))
        
        return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))

    @app.route('/admin/matches/edit', methods=['POST'])
    @login_required
    def edit_match():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                match_id = request.form.get('match_id')
                team1_id = request.form.get('team1_id')
                team2_id = request.form.get('team2_id')
                start_time = request.form.get('start_time')
                field_number = request.form.get('field_number')
                
                match = Match.query.get_or_404(match_id)
                
                if match.status != 'planned':
                    flash('Można edytować tylko zaplanowane mecze', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
                
                if not all([team1_id, team2_id, start_time]):
                    flash('Wszystkie pola są wymagane', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
                
                if team1_id == team2_id:
                    flash('Drużyny muszą być różne', 'danger')
                    return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
                
                # Convert local time input to UTC for storage
                local_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
                utc_time = local_to_utc(local_time)
                
                match.team1_id = team1_id
                match.team2_id = team2_id
                match.start_time = utc_time
                if field_number:
                    match.field_number = field_number
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='edit_match',
                    details=f'Edytowano mecz ID: {match_id}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Mecz został zaktualizowany', 'success')
                return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas edycji meczu: {str(e)}')
                flash('Wystąpił błąd podczas edycji meczu', 'danger')
                return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))
        
        return redirect(url_for('tournament_matches', tournament_id=match.tournament_id))

    @app.route('/admin/years/edit', methods=['POST'])
    @login_required
    def edit_year():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                year_id = request.form.get('year_id')
                year_value = request.form.get('year')
                
                if not all([year_id, year_value]):
                    flash('Wszystkie pola są wymagane', 'danger')
                    return redirect(url_for('admin.manage_years'))
                
                year = Year.query.get_or_404(year_id)
                year.year = int(year_value)
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='edit_year',
                    details=f'Zaktualizowano rocznik: {year.year}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Rocznik został zaktualizowany', 'success')
                return redirect(url_for('admin.manage_years'))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas edycji rocznika: {str(e)}')
                flash('Wystąpił błąd podczas edycji rocznika', 'danger')
                return redirect(url_for('admin.manage_years'))
        
        return redirect(url_for('admin.manage_years'))

    @app.route('/admin/teams/edit', methods=['POST'])
    @login_required
    def edit_team():
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Brak uprawnień', 'danger')
            return redirect(url_for('auth.login'))
        
        form = EmptyForm()
        if form.validate_on_submit():
            try:
                team_id = request.form.get('team_id')
                name = request.form.get('name')
                
                if not team_id or not name:
                    flash('Wszystkie pola są wymagane', 'danger')
                    return redirect(url_for('tournament_teams', tournament_id=request.form.get('tournament_id')))
                
                team = Team.query.get_or_404(team_id)
                tournament = team.tournament
                
                # Sprawdź czy turniej pozwala na edycję drużyn
                if tournament.status != 'planned':
                    flash('Można edytować drużyny tylko w zaplanowanych turniejach', 'danger')
                    return redirect(url_for('tournament_teams', tournament_id=tournament.id))
                
                # Aktualizuj dane drużyny
                team.name = name
                
                # Dodaj log
                log = SystemLog(
                    type='info',
                    user=current_user.email,
                    action='edit_team',
                    details=f'Zaktualizowano drużynę: {team.name}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Drużyna została zaktualizowana', 'success')
                return redirect(url_for('tournament_teams', tournament_id=tournament.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Błąd podczas edycji drużyny: {str(e)}')
                flash('Wystąpił błąd podczas edycji drużyny', 'danger')
                return redirect(url_for('tournament_teams', tournament_id=request.form.get('tournament_id')))
        
        return redirect(url_for('tournament_teams', tournament_id=request.form.get('tournament_id')))

    @app.route('/admin/tournaments/<int:tournament_id>/generate-matches', methods=['POST'])
    @login_required
    def generate_tournament_matches(tournament_id):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Brak uprawnień'}), 403
        
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            
            if tournament.status != 'planned':
                return jsonify({'success': False, 'message': 'Można generować mecze tylko dla zaplanowanych turniejów'}), 400
            
            # Pobierz wszystkie drużyny turnieju
            teams = Team.query.filter_by(tournament_id=tournament_id).all()
            if len(teams) < 2:
                return jsonify({'success': False, 'message': 'Potrzebne są co najmniej 2 drużyny do wygenerowania meczy'}), 400
            
            # Pobierz parametry z formularza
            start_time_str = request.form.get('start_time')
            is_preview = request.args.get('preview', 'false').lower() == 'true'
            
            if not start_time_str:
                return jsonify({'success': False, 'message': 'Wymagana jest data rozpoczęcia'}), 400
            
            try:
                # Konwertuj czas lokalny na UTC
                start_time_local = datetime.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                start_time = local_to_utc(start_time_local)
                
                # Sprawdź czy data nie jest w przeszłości
                if start_time < datetime.datetime.now(datetime.timezone.utc):
                    return jsonify({'success': False, 'message': 'Data rozpoczęcia nie może być w przeszłości'}), 400
            except ValueError:
                return jsonify({'success': False, 'message': 'Nieprawidłowy format daty'}), 400
            
            # Generuj mecze każdy z każdym
            matches = []
            current_time = start_time
            field_number = 1
            
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    # Konwertuj czas UTC na lokalny i formatuj
                    local_time = current_time.replace(tzinfo=datetime.timezone.utc).astimezone()
                    formatted_time = local_time.strftime('%H:%M')
                    
                    match = {
                        'team1': teams[i].name,
                        'team2': teams[j].name,
                        'start_time': formatted_time,
                        'field': field_number
                    }
                    matches.append(match)
                    
                    # Przejdź do następnego czasu i boiska
                    current_time += datetime.timedelta(minutes=tournament.match_length + tournament.break_length)
                    field_number = (field_number % tournament.number_of_fields) + 1
            
            # Jeśli to tylko podgląd, zwróć listę meczy
            if is_preview:
                return jsonify({
                    'success': True,
                    'matches': matches
                })
            
            # W przeciwnym razie zapisz mecze w bazie
            for match_data in matches:
                # Utwórz pełną datę z godziną
                match_time = start_time_local.replace(
                    hour=int(match_data['start_time'].split(':')[0]),
                    minute=int(match_data['start_time'].split(':')[1])
                )
                match_time_utc = local_to_utc(match_time)
                
                team1 = next(t for t in teams if t.name == match_data['team1'])
                team2 = next(t for t in teams if t.name == match_data['team2'])
                
                match = Match(
                    tournament_id=tournament_id,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    start_time=match_time_utc,
                    field_number=match_data['field'],
                    status='planned'
                )
                db.session.add(match)
            
            # Dodaj log
            log = SystemLog(
                type='info',
                user=current_user.email,
                action='generate_matches',
                details=f'Wygenerowano {len(matches)} meczy dla turnieju: {tournament.name}'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Wygenerowano {len(matches)} meczy',
                'redirect_url': url_for('admin.tournament_matches', tournament_id=tournament_id)
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Błąd podczas generowania meczy: {str(e)}')
            return jsonify({'success': False, 'message': 'Wystąpił błąd podczas generowania meczy'}), 500

def utc_to_local(utc_dt):
    if utc_dt is None:
        return None
    try:
        # Ensure the datetime is UTC aware
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=datetime.timezone.utc)
        # Get local timezone
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        # Convert to local time
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        app.logger.error(f'Error converting UTC to local time: {str(e)}')
        # Return original datetime formatted as string if conversion fails
        try:
            return utc_dt.strftime('%d.%m.%Y %H:%M')
        except:
            return str(utc_dt)

def local_to_utc(local_dt_str):
    if local_dt_str is None:
        return None
    try:
        # Parse the local datetime string (expected format: DD.MM.YYYY HH:MM or YYYY-MM-DD HH:MM)
        try:
            local_dt = datetime.datetime.strptime(local_dt_str, '%d.%m.%Y %H:%M')
        except ValueError:
            local_dt = datetime.datetime.strptime(local_dt_str, '%Y-%m-%d %H:%M')
        
        # Get local timezone
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        # Make datetime timezone-aware
        local_dt = local_dt.replace(tzinfo=local_tz)
        # Convert to UTC
        return local_dt.astimezone(datetime.timezone.utc)
    except Exception as e:
        app.logger.error(f'Error converting local time to UTC: {str(e)}')
        return None

class EmptyForm(FlaskForm):
    pass