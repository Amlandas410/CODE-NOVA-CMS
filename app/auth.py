from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from .db import query
from mysql.connector import Error

bp = Blueprint('auth', __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identity = request.form.get('identity', '').strip()
        password = request.form.get('password', '')
        try:
            user = query("SELECT * FROM users WHERE active=1 AND (email=%s OR student_id=%s)", (identity,identity), one=True)
        except Error:
            flash('Campus database is not available. Check MySQL and the .env settings.', 'danger')
            return render_template('auth/login.html'), 503
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session.permanent = True
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['lang'] = user.get('preferred_language') or 'en'
            session['user_name'] = user.get('name') or ''
            session['user_email'] = user.get('email') or ''
            if user['role']=='student':
                return redirect(url_for('student.dashboard'))
            if user['role']=='admin': return redirect(url_for('admin.dashboard'))
            if user['role']=='teacher': return redirect(url_for('teacher.dashboard'))
            if user['role']=='warden': return redirect(url_for('warden.dashboard'))
            return redirect(url_for('auth.logout'))
        flash('Invalid ID/email or password.', 'danger')
    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
