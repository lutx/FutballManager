from flask import Blueprint, redirect, url_for, session
from flask_login import current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Root route that redirects users based on their authentication status and role."""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
    
    if 'role' in session and session['role'] == 'parent':
        return redirect(url_for('parent.select_year'))
        
    return redirect(url_for('auth.login')) 