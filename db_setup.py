import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

def setup_database():
    # Define database directory and path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Set database path
    db_path = os.path.join(data_dir, 'weather_app.db')
    
    print(f"Setting up database at: {db_path}")
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT UNIQUE,
        is_admin BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create user_settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        default_city TEXT,
        temperature_unit TEXT DEFAULT 'celsius',
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # Create saved_locations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        city_name TEXT NOT NULL,
        display_name TEXT,
        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE(user_id, city_name)
    )
    ''')
    
    # Create default admin user if not exists
    try:
        default_admin = {
            'username': 'admin',
            'password': 'adminpassword',  # Change this in production
            'email': 'admin@example.com',
            'is_admin': 1
        }
        
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)",
            (
                default_admin['username'],
                generate_password_hash(default_admin['password']),
                default_admin['email'],
                default_admin['is_admin']
            )
        )
        
        if cursor.rowcount > 0:
            print("Default admin user created")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_saved_locations_user_id ON saved_locations (user_id)")
    
    # Set pragmas for better performance and reliability
    cursor.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database setup complete")
    
    # Set appropriate file permissions on Unix systems
    if sys.platform != 'win32':
        try:
            os.chmod(db_path, 0o600)
            print(f"Set file permissions to 0600 for {db_path}")
        except Exception as e:
            print(f"Failed to set file permissions: {e}")

if __name__ == "__main__":
    setup_database()