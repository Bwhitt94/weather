import sqlite3
import os
from flask import g

# Get the database path
def get_db_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)  # Create data directory if it doesn't exist
    return os.path.join(data_dir, 'weather_app.db')

# For standalone scripts (non-Flask context)
def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

# For use within Flask application
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(get_db_path())
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

# Close the database connection
def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Execute a query and return results - works both in Flask and standalone
def query_db(query, args=(), one=False):
    try:
        # Try to use Flask's g object first
        from flask import has_app_context
        if has_app_context():
            conn = get_db()
            own_connection = False
        else:
            raise RuntimeError("No Flask app context")
    except (ImportError, RuntimeError):
        # Fallback to direct connection for non-Flask usage
        conn = get_db_connection()
        own_connection = True
    
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    finally:
        if own_connection:
            conn.close()

# Insert data and return the last row ID
def insert_db(query, args=()):
    try:
        # Try to use Flask's g object first
        from flask import has_app_context
        if has_app_context():
            conn = get_db()
            own_connection = False
        else:
            raise RuntimeError("No Flask app context")
    except (ImportError, RuntimeError):
        # Fallback to direct connection for non-Flask usage
        conn = get_db_connection()
        own_connection = True
    
    try:
        cur = conn.execute(query, args)
        conn.commit()
        return cur.lastrowid
    finally:
        if own_connection:
            conn.close()

# Update data and return number of affected rows
def update_db(query, args=()):
    try:
        # Try to use Flask's g object first
        from flask import has_app_context
        if has_app_context():
            conn = get_db()
            own_connection = False
        else:
            raise RuntimeError("No Flask app context")
    except (ImportError, RuntimeError):
        # Fallback to direct connection for non-Flask usage
        conn = get_db_connection()
        own_connection = True
    
    try:
        cur = conn.execute(query, args)
        conn.commit()
        return cur.rowcount
    finally:
        if own_connection:
            conn.close()