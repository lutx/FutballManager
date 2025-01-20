from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from models import User, Year, Tournament, Team, Match, SystemLog, SystemSettings
from extensions import db, bcrypt
from services.logging_service import LoggingService
from services.tournament_service import TournamentService
from services.match_service import MatchService
from forms.admin import EmptyForm, YearForm, TournamentForm, TeamForm, MatchForm, AdminForm
from decorators import admin_required, primary_admin_required
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import pytz

bp = Blueprint('admin', __name__, url_prefix='/admin')

def local_to_utc(local_dt):
    """Konwertuje czas lokalny na UTC"""
    local_tz = pytz.timezone('Europe/Warsaw')  # Strefa czasowa Polski
    local_dt = local_tz.localize(local_dt)
    return local_dt.astimezone(pytz.UTC)

def utc_to_local(utc_dt):
    """Konwertuje czas UTC na lokalny"""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    local_tz = pytz.timezone('Europe/Warsaw')  # Strefa czasowa Polski
    return utc_dt.astimezone(local_tz)

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
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
        current_app.logger.error(f'Błąd bazy danych: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f'Nieoczekiwany błąd: {str(e)}')
        flash('Wystąpił nieoczekiwany błąd', 'danger')
        return redirect(url_for('auth.login'))

@bp.route('/manage')
@login_required
@primary_admin_required
def manage_admins():
    try:
        admins = User.query.filter_by(role='admin').all()
        form = AdminForm()
        return render_template('admin/manage_admins.html', admins=admins, form=form)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania administratorów: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('admin.dashboard'))

@bp.route('/manage/add', methods=['POST'])
@login_required
@primary_admin_required
def add_admin():
    form = AdminForm()
    if form.validate_on_submit():
        try:
            email = form.email.data
            password = form.password.data
            
            if User.query.filter_by(email=email).first():
                flash('Ten email jest już zajęty', 'danger')
                return redirect(url_for('admin.manage_admins'))
            
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_admin = User(email=email, password=hashed_password, role='admin')
            db.session.add(new_admin)
            
            # Dodaj log
            log = SystemLog(
                type='warning',
                user=current_user.email,
                action='add_admin',
                details=f'Dodano nowego administratora: {email}'
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Administrator został dodany', 'success')
            return redirect(url_for('admin.manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Błąd podczas dodawania administratora: {str(e)}')
            flash('Wystąpił błąd podczas dodawania administratora', 'danger')
            return redirect(url_for('admin.manage_admins'))
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    return redirect(url_for('admin.manage_admins'))

@bp.route('/manage/delete/<int:admin_id>', methods=['POST'])
@login_required
@primary_admin_required
def delete_admin(admin_id):
    form = EmptyForm()
    if form.validate_on_submit():
        try:
            admin = User.query.get_or_404(admin_id)
            
            if admin.is_primary_admin:
                flash('Nie można usunąć głównego administratora', 'danger')
                return redirect(url_for('admin.manage_admins'))
            
            # Dodaj log przed usunięciem
            log = SystemLog(
                type='warning',
                user=current_user.email,
                action='delete_admin',
                details=f'Usunięto administratora: {admin.email}'
            )
            db.session.add(log)
            
            db.session.delete(admin)
            db.session.commit()
            
            flash('Administrator został usunięty', 'success')
            return redirect(url_for('admin.manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Błąd podczas usuwania administratora: {str(e)}')
            flash('Wystąpił błąd podczas usuwania administratora', 'danger')
            return redirect(url_for('admin.manage_admins'))
    
    return redirect(url_for('admin.manage_admins'))

@bp.route('/logo', methods=['GET', 'POST', 'DELETE'])
@login_required
@primary_admin_required
def manage_logo():
    try:
        form = EmptyForm()
        
        if request.method == 'DELETE':
            logo = SystemSettings.query.filter_by(key='logo_path').first()
            if logo:
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', logo.value))
                except:
                    pass
                db.session.delete(logo)
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
                        os.remove(os.path.join(current_app.root_path, 'static', old_logo.value))
                    except:
                        pass
                
                # Zapisz nowe logo
                filename = secure_filename(f"logo_{int(datetime.datetime.now().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(current_app.root_path, 'static', 'uploads', filename))
                
                # Zapisz ścieżkę do logo w ustawieniach
                if old_logo:
                    old_logo.value = f'uploads/{filename}'
                else:
                    setting = SystemSettings(key='logo_path', value=f'uploads/{filename}')
                    db.session.add(setting)
                
                db.session.commit()
                flash('Logo zostało zaktualizowane', 'success')
                return redirect(url_for('admin.manage_logo'))
            else:
                flash('Niedozwolony format pliku', 'danger')
        
        logo_path = SystemSettings.query.filter_by(key='logo_path').first()
        return render_template('admin/manage_logo.html', 
                            logo_path=logo_path.value if logo_path else None,
                            form=form)
        
    except Exception as e:
        current_app.logger.error(f'Błąd podczas zarządzania logo: {str(e)}')
        flash('Wystąpił błąd podczas zarządzania logo', 'danger')
        return redirect(url_for('admin.dashboard'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/view_logs')
@login_required
@primary_admin_required
def view_logs():
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
        
        # Unikalne wartości dla filtrów
        unique_types = db.session.query(SystemLog.type.distinct()).all()
        unique_actions = db.session.query(SystemLog.action.distinct()).all()
        unique_users = db.session.query(SystemLog.user.distinct()).all()
        
        return render_template('admin/view_logs.html',
                           logs=logs,
                           unique_types=[t[0] for t in unique_types],
                           unique_actions=[a[0] for a in unique_actions],
                           unique_users=[u[0] for u in unique_users])
                           
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania logów: {str(e)}')
        flash('Wystąpił błąd podczas ładowania logów', 'danger')
        return redirect(url_for('admin.dashboard'))

@bp.route('/logs/clear', methods=['POST'])
@login_required
@primary_admin_required
def clear_logs():
    try:
        # Usuń wszystkie logi starsze niż 30 dni
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        SystemLog.query.filter(SystemLog.timestamp < thirty_days_ago).delete()
        db.session.commit()
        
        flash('Stare logi zostały usunięte', 'success')
        return redirect(url_for('admin.view_logs'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas czyszczenia logów: {str(e)}')
        flash('Wystąpił błąd podczas czyszczenia logów', 'danger')
        return redirect(url_for('admin.view_logs'))

@bp.route('/years', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_years():
    try:
        form = YearForm()
        if form.validate_on_submit():
            year = Year(year=form.year.data)
            db.session.add(year)
            
            # Dodaj log
            log = SystemLog(
                type='info',
                user=current_user.email,
                action='add_year',
                details=f'Dodano nowy rocznik: {year.year}'
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Rocznik został dodany', 'success')
            return redirect(url_for('admin.manage_years'))
            
        years = Year.query.order_by(Year.year.desc()).all()
        return render_template('admin/years.html', years=years, form=form)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas operacji na rocznikach: {str(e)}')
        flash('Wystąpił błąd podczas operacji na rocznikach', 'danger')
        return redirect(url_for('admin.dashboard'))

@bp.route('/years/<int:year_id>/delete', methods=['POST'])
@login_required
@admin_required
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
            current_app.logger.error(f'Błąd podczas usuwania rocznika: {str(e)}')
            flash('Wystąpił błąd podczas usuwania rocznika', 'danger')
            return redirect(url_for('admin.manage_years'))
    
    return redirect(url_for('admin.manage_years'))

@bp.route('/years/<int:year_id>/tournaments')
@login_required
@admin_required
def year_tournaments(year_id):
    try:
        year = Year.query.get_or_404(year_id)
        tournaments = Tournament.query.filter_by(year_id=year_id).order_by(Tournament.id.desc()).all()
        form = TournamentForm()
        
        return render_template('admin/year_tournaments.html', 
                             year=year, 
                             tournaments=tournaments, 
                             form=form)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania turniejów: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('admin.manage_years'))

@bp.route('/years/edit', methods=['POST'])
@login_required
@admin_required
def edit_year():
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
            current_app.logger.error(f'Błąd podczas edycji rocznika: {str(e)}')
            flash('Wystąpił błąd podczas edycji rocznika', 'danger')
            return redirect(url_for('admin.manage_years'))
    
    return redirect(url_for('admin.manage_years'))

@bp.route('/tournaments/add', methods=['POST'])
@login_required
@admin_required
def add_tournament():
    form = TournamentForm()
    if form.validate_on_submit():
        try:
            year_id = request.form.get('year_id')
            
            new_tournament = Tournament(
                name=form.name.data,
                year_id=year_id,
                status='planned',
                address=form.address.data,
                number_of_fields=form.number_of_fields.data,
                match_length=form.match_length.data,
                break_length=form.break_length.data
            )
            
            db.session.add(new_tournament)
            db.session.commit()
            
            current_app.logger.info(
                f'Dodano nowy turniej: {form.name.data}',
                extra={
                    'user': current_user.email,
                    'action': 'add_tournament'
                }
            )
            
            flash(f'Turniej {form.name.data} został dodany pomyślnie', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f'Błąd podczas dodawania turnieju: {str(e)}',
                extra={
                    'user': current_user.email,
                    'action': 'add_tournament'
                }
            )
            flash('Wystąpił błąd podczas dodawania turnieju', 'danger')
            
        return redirect(url_for('admin.year_tournaments', year_id=year_id))
    
    flash('Nieprawidłowe żądanie', 'danger')
    return redirect(url_for('admin.dashboard'))

@bp.route('/tournaments/<int:tournament_id>/teams')
@login_required
@admin_required
def tournament_teams(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        form = TeamForm()
        return render_template('admin/tournament_teams.html', 
                             tournament=tournament, 
                             teams=teams,
                             form=form)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania drużyn: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

@bp.route('/teams/add', methods=['POST'])
@login_required
@admin_required
def add_team():
    form = TeamForm()
    if form.validate_on_submit():
        try:
            tournament_id = request.form.get('tournament_id')
            tournament = Tournament.query.get_or_404(tournament_id)
            
            if tournament.status != 'planned':
                flash('Można dodawać drużyny tylko do zaplanowanych turniejów', 'danger')
                return redirect(url_for('admin.tournament_teams', tournament_id=tournament_id))
            
            new_team = Team(
                name=form.name.data,
                tournament_id=tournament_id
            )
            db.session.add(new_team)
            
            # Dodaj log
            log = SystemLog(
                type='info',
                user=current_user.email,
                action='add_team',
                details=f'Dodano nową drużynę: {form.name.data} do turnieju: {tournament.name}'
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Drużyna została dodana', 'success')
            return redirect(url_for('admin.tournament_teams', tournament_id=tournament_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Błąd podczas dodawania drużyny: {str(e)}')
            flash('Wystąpił błąd podczas dodawania drużyny', 'danger')
            return redirect(url_for('admin.tournament_teams', tournament_id=tournament_id))
    
    # W przypadku błędów walidacji formularza
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('admin.tournament_teams', tournament_id=request.form.get('tournament_id')))

@bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_team(team_id):
    form = EmptyForm()
    if form.validate_on_submit():
        try:
            team = Team.query.get_or_404(team_id)
            tournament = team.tournament
            
            if tournament.status != 'planned':
                flash('Można usuwać drużyny tylko z zaplanowanych turniejów', 'danger')
                return redirect(url_for('admin.tournament_teams', tournament_id=tournament.id))
            
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
            return redirect(url_for('admin.tournament_teams', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Błąd podczas usuwania drużyny: {str(e)}')
            flash('Wystąpił błąd podczas usuwania drużyny', 'danger')
            return redirect(url_for('admin.tournament_teams', tournament_id=tournament.id))
    
    return redirect(url_for('admin.tournament_teams', tournament_id=team.tournament_id))

@bp.route('/teams/edit', methods=['POST'])
@login_required
@admin_required
def edit_team():
    form = EmptyForm()
    if form.validate_on_submit():
        try:
            team_id = request.form.get('team_id')
            name = request.form.get('name')
            
            if not team_id or not name:
                flash('Wszystkie pola są wymagane', 'danger')
                return redirect(url_for('admin.tournament_teams', tournament_id=request.form.get('tournament_id')))
            
            team = Team.query.get_or_404(team_id)
            tournament = team.tournament
            
            # Sprawdź czy turniej pozwala na edycję drużyn
            if tournament.status != 'planned':
                flash('Można edytować drużyny tylko w zaplanowanych turniejach', 'danger')
                return redirect(url_for('admin.tournament_teams', tournament_id=tournament.id))
            
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
            return redirect(url_for('admin.tournament_teams', tournament_id=tournament.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Błąd podczas edycji drużyny: {str(e)}')
            flash('Wystąpił błąd podczas edycji drużyny', 'danger')
            return redirect(url_for('admin.tournament_teams', tournament_id=request.form.get('tournament_id')))
    
    return redirect(url_for('admin.tournament_teams', tournament_id=request.form.get('tournament_id')))

@bp.route('/tournaments/<int:tournament_id>/matches')
@login_required
@admin_required
def tournament_matches(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        if not tournament:
            flash('Nie znaleziono turnieju', 'danger')
            return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))
            
        # Sortowanie meczów po czasie rozpoczęcia
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.start_time.asc()).all()
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        
        # Przygotuj formularz z listą drużyn i dostępnymi boiskami
        form = MatchForm()
        form.team1_id.choices = [(team.id, team.name) for team in teams]
        form.team2_id.choices = [(team.id, team.name) for team in teams]
        
        # Ustaw dostępne boiska
        form.field_number.choices = [(i, f"Boisko {i}") for i in range(1, tournament.number_of_fields + 1)]
        
        # Ustaw domyślny czas rozpoczęcia na czas rozpoczęcia turnieju
        if not matches and tournament.date and tournament.start_time:  # Jeśli to pierwszy mecz
            form.start_time.data = datetime.combine(tournament.date, tournament.start_time)
        
        return render_template('admin/tournament_matches.html', 
                             tournament=tournament,
                             matches=matches,
                             teams=teams,
                             form=form)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania meczów: {str(e)}')
        flash(f'Błąd podczas ładowania meczów: {str(e)}', 'danger')
        return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

@bp.route('/tournaments/<int:tournament_id>/results')
@login_required
@admin_required
def tournament_results(tournament_id):
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        matches = Match.query.filter_by(tournament_id=tournament_id).all()
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        
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
        
        return render_template('admin/tournament_results.html',
                             tournament=tournament,
                             team_stats=team_stats)
    except Exception as e:
        current_app.logger.error(f'Błąd podczas ładowania wyników: {str(e)}')
        flash('Wystąpił błąd podczas ładowania danych', 'danger')
        return redirect(url_for('admin.year_tournaments', year_id=tournament.year_id))

@bp.route('/matches/add', methods=['POST'])
@login_required
@admin_required
def add_match():
    try:
        tournament_id = request.form.get('tournament_id')
        tournament = Tournament.query.get_or_404(tournament_id)
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        
        # Initialize form with choices
        form = MatchForm()
        form.team1_id.choices = [(team.id, team.name) for team in teams]
        form.team2_id.choices = [(team.id, team.name) for team in teams]
        form.field_number.choices = [(i, f"Boisko {i}") for i in range(1, tournament.number_of_fields + 1)]
        
        if form.validate_on_submit():
            # Sprawdź czy turniej ma wystarczającą liczbę drużyn
            if len(tournament.teams) < 2:
                flash('Nie można dodać meczu - wymagane są co najmniej 2 drużyny', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            
            # Sprawdź status turnieju
            if tournament.status == 'finished':
                flash('Nie można dodawać meczów do zakończonego turnieju', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            elif tournament.status == 'ongoing' and not current_user.is_primary_admin:
                flash('Tylko główny administrator może dodawać mecze do trwającego turnieju', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            
            # Sprawdź czy drużyny są różne
            if form.team1_id.data == form.team2_id.data:
                flash('Drużyny muszą być różne', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))

            # Sprawdź czy drużyny należą do tego turnieju
            team1 = Team.query.get_or_404(form.team1_id.data)
            team2 = Team.query.get_or_404(form.team2_id.data)
            if team1.tournament_id != int(tournament_id) or team2.tournament_id != int(tournament_id):
                flash('Wybrane drużyny nie należą do tego turnieju', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            
            # Convert local time input to UTC for storage
            try:
                local_time = form.start_time.data
                if local_time.tzinfo is None:  # Jeśli czas nie ma informacji o strefie czasowej
                    utc_time = local_to_utc(local_time)
                else:
                    utc_time = local_time.astimezone(pytz.UTC)
            except Exception as e:
                current_app.logger.error(f'Błąd konwersji czasu: {str(e)}')
                flash('Błąd podczas przetwarzania daty i czasu', 'danger')
                return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            
            new_match = Match(
                tournament_id=tournament_id,
                team1_id=form.team1_id.data,
                team2_id=form.team2_id.data,
                start_time=utc_time,
                field_number=form.field_number.data,
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
            
            flash('Mecz został dodany', 'success')
            return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Błąd podczas dodawania meczu: {str(e)}')
        flash('Wystąpił błąd podczas dodawania meczu', 'danger')
        return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
    
    return redirect(url_for('admin.tournament_matches', tournament_id=request.form.get('tournament_id')))

@bp.route('/tournaments/<int:tournament_id>/generate_matches', methods=['POST'])
@login_required
@admin_required
def generate_matches(tournament_id):
    try:
        form = EmptyForm()
        if not form.validate_on_submit():
            flash('Błąd walidacji formularza', 'danger')
            return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
        
        # Pobierz dane z formularza i utwórz prawidłowy obiekt datetime
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        start_datetime = datetime.combine(start_date, start_time)
        
        fields_count = int(request.form['fields_count'])
        match_duration = int(request.form['match_duration'])
        break_duration = int(request.form['break_duration'])
        
        # Zaktualizuj turniej
        tournament_service = TournamentService()
        tournament = tournament_service.get_tournament(tournament_id)
        if not tournament:
            flash('Nie znaleziono turnieju', 'danger')
            return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
        
        # Aktualizuj ustawienia turnieju
        success = tournament_service.update_tournament(
            tournament_id,
            start_time=start_datetime,  # Przekaż pełny obiekt datetime
            number_of_fields=fields_count,
            match_length=match_duration,
            break_length=break_duration
        )
        
        if not success:
            flash('Wystąpił błąd podczas aktualizacji ustawień turnieju', 'danger')
            return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
        
        # Generuj mecze
        if tournament_service.generate_matches(tournament_id):
            flash('Mecze zostały wygenerowane', 'success')
        else:
            flash('Wystąpił błąd podczas generowania meczów', 'danger')
        
        return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id))
        
    except Exception as e:
        current_app.logger.error(f'Błąd podczas generowania meczów: {str(e)}')
        flash('Wystąpił błąd podczas generowania meczów', 'danger')
        return redirect(url_for('admin.tournament_matches', tournament_id=tournament_id)) 