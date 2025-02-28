from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from functools import wraps
from flask import redirect, url_for, request
from db import query_db, insert_db, update_db
import sqlite3

# Register a new user
def register_user(username, password, email=None):
    try:
        user_id = insert_db(
            'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), email)
        )
        
        # Create default user settings
        insert_db(
            'INSERT INTO user_settings (user_id, default_city, temperature_unit) VALUES (?, ?, ?)',
            (user_id, '', 'celsius')
        )
        
        return user_id
    except sqlite3.IntegrityError:
        # Username or email already exists
        return None

# Authenticate a user
def authenticate_user(username, password):
    user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
    
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

# Get a user by ID
def get_user(user_id):
    return query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)

# Get user settings
def get_user_settings(user_id):
    return query_db('SELECT * FROM user_settings WHERE user_id = ?', (user_id,), one=True)

# Update user settings
def update_user_settings(user_id, default_city, temperature_unit):
    # Check if settings exist
    settings = get_user_settings(user_id)
    
    if settings:
        return update_db(
            'UPDATE user_settings SET default_city = ?, temperature_unit = ? WHERE user_id = ?',
            (default_city, temperature_unit, user_id)
        )
    else:
        return insert_db(
            'INSERT INTO user_settings (user_id, default_city, temperature_unit) VALUES (?, ?, ?)',
            (user_id, default_city, temperature_unit)
        )

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        # Check if user is admin
        user = get_user(session['user_id'])
        if not user or not user['is_admin']:
            return redirect(url_for('home'))
            
        return f(*args, **kwargs)
    return decorated_function