from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from .storage import storage

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = storage.find_user_by_email(email)
        if user and user.check_password(password) and user.active:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    flash('Self-registration is currently disabled. Please contact your administrator.', 'warning')
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        storage.save_users()
        flash('Profile updated', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('profile.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')
        if not current_user.check_password(old):
            flash('Old password incorrect', 'danger')
            return redirect(url_for('auth.change_password'))
        current_user.set_password(new)
        storage.save_users()
        flash('Password changed', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('change_password.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = storage.find_user_by_email(email)
        flash('If an account exists, password reset instructions were sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')
