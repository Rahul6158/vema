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
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        
        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.register'))
            
        existing_user = storage.find_user_by_email(email)
        if existing_user:
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))
            
        new_user = User(name=name, email=email, phone=phone, active=True)
        new_user.set_password(password)
        
        staff_role = storage.find_role_by_name('Staff') or storage.find_role_by_name('User')
        if staff_role:
            new_user.role_id = staff_role.id
            
        storage.add_user(new_user)
        login_user(new_user)
        flash('Account created successfully! Welcome to VEMA CRM.', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('register.html')


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
