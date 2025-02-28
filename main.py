from dotenv import load_dotenv
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, g
import requests
import time
import datetime
import json
from termcolor import colored
import shutil
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables
load_dotenv()
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Initialize Flask app with the correct template directory
script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, 'templates')
app = Flask(__name__, template_folder=templates_dir)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Get terminal size
terminal_width, _ = shutil.get_terminal_size()

# Database setup
def get_db_path():
    data_dir = os.path.join(script_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'weather_app.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(get_db_path())
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with sqlite3.connect(get_db_path()) as conn:
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
            
        except Exception as e:
            print(f"Error creating admin user: {e}")
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_saved_locations_user_id ON saved_locations (user_id)")
        
        conn.commit()
        print("Database initialized")

# Register database functions
app.teardown_appcontext(close_db)

# Authentication functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        # Check if user is admin
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or not user['is_admin']:
            flash('Access denied: Admin privileges required')
            return redirect(url_for('home'))
            
        return f(*args, **kwargs)
    return decorated_function

# ANSI color codes for more vibrant terminal output
class TermColors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BACKGROUND_BLUE = '\033[44m'
    BACKGROUND_GREEN = '\033[42m'
    BACKGROUND_YELLOW = '\033[43m'
    BACKGROUND_RED = '\033[41m'

# Display a cool banner when starting the app
def display_weather_banner():
    """Display a cool ASCII art weather banner with animation effect"""
    banner = """
    ╭──────────────────────────────────────────────────────╮
    │                                                      │
    │   ☁️  ☀️  🌦️  LIVE WEATHER FORECAST API 🌧️  ❄️  🌈   │
    │                                                      │
    │   ┌───────────────┐        ┌─────────────────────┐  │
    │   │  TEMPERATURE  │        │  POWERED BY WEATHER │  │
    │   │    ° F│° C    │◀──────▶│        API          │  │
    │   └───────────────┘        └─────────────────────┘  │
    │                                                      │
    │      REAL-TIME UPDATES & LIVE WEATHER METRICS       │
    │                                                      │
    ╰──────────────────────────────────────────────────────╯
    """
    
    # For simple animation effect
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    # Print the banner character by character
    for char in banner:
        print(char, end='', flush=True)
        time.sleep(0.001)  # Slightly faster animation
    
    print("\n")  # Add some space after the banner

def get_weather_condition_icon(condition_text):
    """Return an appropriate weather icon based on condition text"""
    condition_text = condition_text.lower()
    
    if 'sunny' in condition_text or 'clear' in condition_text:
        return '☀️'
    elif 'partly cloudy' in condition_text:
        return '⛅'
    elif 'cloudy' in condition_text or 'overcast' in condition_text:
        return '☁️'
    elif 'rain' in condition_text or 'drizzle' in condition_text:
        return '🌧️'
    elif 'thunder' in condition_text or 'lightning' in condition_text:
        return '⛈️'
    elif 'snow' in condition_text or 'blizzard' in condition_text:
        return '❄️'
    elif 'mist' in condition_text or 'fog' in condition_text:
        return '🌫️'
    else:
        return '🌡️'

def get_temp_color(temp_c):
    """Return appropriate color based on temperature"""
    if temp_c >= 35:
        return TermColors.RED
    elif temp_c >= 25:
        return TermColors.YELLOW
    elif temp_c >= 15:
        return TermColors.GREEN
    elif temp_c >= 5:
        return TermColors.CYAN
    else:
        return TermColors.BLUE

def get_wind_direction_arrow(wind_dir):
    """Return arrow symbol based on wind direction"""
    wind_arrows = {
        'N': '↓', 'NNE': '↓↙', 'NE': '↙', 'ENE': '↙←',
        'E': '←', 'ESE': '←↖', 'SE': '↖', 'SSE': '↖↑',
        'S': '↑', 'SSW': '↑↗', 'SW': '↗', 'WSW': '↗→',
        'W': '→', 'WNW': '→↘', 'NW': '↘', 'NNW': '↘↓'
    }
    return wind_arrows.get(wind_dir, '?')

def create_progress_bar(value, max_value, width=20, fill_char='█', empty_char='░'):
    """Create a visual progress bar"""
    percent = min(value / max_value, 1.0)
    filled_length = int(width * percent)
    bar = fill_char * filled_length + empty_char * (width - filled_length)
    return bar

def display_terminal_weather(weather_data):
    """Display weather data in a visually appealing format in the terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    # Extract relevant data
    location = weather_data['location']
    current = weather_data['current']
    
    # Get icon and colors
    weather_icon = get_weather_condition_icon(current['condition']['text'])
    temp_color = get_temp_color(current['temp_c'])
    wind_arrow = get_wind_direction_arrow(current['wind_dir'])
    
    # Create header
    print("╭" + "─" * (terminal_width - 2) + "╮")
    
    # Location header with timestamp
    location_str = f"{location['name']}, {location['region']}, {location['country']}"
    timestamp = f"Local time: {location['localtime']}"
    padding = terminal_width - len(location_str) - len(timestamp) - 4
    print(f"│ {TermColors.BOLD}{location_str}{TermColors.ENDC}" + " " * padding + f"{timestamp} │")
    
    # Divider
    print("├" + "─" * (terminal_width - 2) + "┤")
    
    # Main weather display - Top section
    condition_text = current['condition']['text']
    temp_c = current['temp_c']
    temp_f = current['temp_f']
    feels_like_c = current['feelslike_c']
    
    # Center-aligned weather condition with icon
    condition_display = f"{weather_icon}  {condition_text}  {weather_icon}"
    condition_padding = (terminal_width - len(condition_display) - 4) // 2
    print(f"│" + " " * condition_padding + f"{TermColors.BOLD}{condition_display}{TermColors.ENDC}" + " " * (terminal_width - len(condition_display) - condition_padding - 2) + "│")
    
    # Temperature display
    temp_display = f"Temperature: {temp_color}{temp_c}°C / {temp_f}°F{TermColors.ENDC} (Feels like: {feels_like_c}°C)"
    temp_padding = (terminal_width - len(temp_display) - 12) // 2  # Account for color codes
    print(f"│" + " " * temp_padding + temp_display + " " * (terminal_width - len(temp_display) - temp_padding - 2 + 12) + "│")
    
    # Divider
    print("├" + "─" * (terminal_width - 2) + "┤")
    
    # Create metrics section - using progress bars
    print(f"│ {TermColors.BOLD}Weather Metrics:{TermColors.ENDC}" + " " * (terminal_width - 18) + "│")
    
    # Humidity bar
    humidity = current['humidity']
    humidity_bar = create_progress_bar(humidity, 100)
    humidity_text = f"Humidity: {humidity}% "
    print(f"│ {humidity_text}{humidity_bar} │")
    
    # Wind speed bar (max 50 mph for scale)
    wind_mph = current['wind_mph']
    wind_kph = current['wind_kph']
    wind_bar = create_progress_bar(wind_mph, 50)
    wind_text = f"Wind: {wind_mph} mph / {wind_kph} kph {wind_arrow} {current['wind_dir']} "
    print(f"│ {wind_text}{wind_bar} │")
    
    # Precipitation bar
    precip_mm = current['precip_mm']
    precip_bar = create_progress_bar(precip_mm, 25)  # 25mm as max for scale
    precip_text = f"Precipitation: {precip_mm} mm "
    print(f"│ {precip_text}{precip_bar} │")
    
    # UV Index bar
    uv = current['uv']
    uv_color = TermColors.GREEN if uv < 3 else TermColors.YELLOW if uv < 6 else TermColors.RED
    uv_bar = create_progress_bar(uv, 11)
    uv_text = f"UV Index: {uv_color}{uv}{TermColors.ENDC} "
    print(f"│ {uv_text}{uv_bar} │")
    
    # Additional data
    print("├" + "─" * (terminal_width - 2) + "┤")
    print(f"│ {TermColors.BOLD}Additional Information:{TermColors.ENDC}" + " " * (terminal_width - 26) + "│")
    
    # Left side
    left_data = [
        f"Pressure: {current['pressure_mb']} mb",
        f"Visibility: {current['vis_km']} km",
        f"Cloud Cover: {current['cloud']}%",
    ]
    
    # Right side
    right_data = [
        f"Wind Gust: {current['gust_mph']} mph",
        f"Updated: {current['last_updated']}",
        f"Coordinates: {location['lat']}, {location['lon']}"
    ]
    
    # Print two columns
    for i in range(len(left_data)):
        left_item = left_data[i]
        right_item = right_data[i]
        padding = terminal_width - len(left_item) - len(right_item) - 4
        print(f"│ {left_item}" + " " * padding + f"{right_item} │")
    
    # Footer
    print("╰" + "─" * (terminal_width - 2) + "╯")
    
    # Print timestamp of display
    print(f"\nTerminal display updated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data will auto-refresh every 60 seconds")
    print(f"Press Ctrl+C to exit the server")

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid username or password', 'error')
            return render_template('login.html')
        
        # Store user information in session
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = bool(user['is_admin'])
        
        # Redirect to the requested page or home
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        
        # Form validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        db = get_db()
        try:
            # Create new user
            db.execute(
                'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), email)
            )
            
            # Get the user ID
            user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            
            # Create default settings for the user
            if user:
                db.execute(
                    'INSERT INTO user_settings (user_id, default_city, temperature_unit) VALUES (?, ?, ?)',
                    (user['id'], '', 'celsius')
                )
                
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    settings = db.execute('SELECT * FROM user_settings WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        default_city = request.form.get('default_city', '')
        temperature_unit = request.form.get('temperature_unit', 'celsius')
        
        try:
            if settings:
                db.execute(
                    'UPDATE user_settings SET default_city = ?, temperature_unit = ? WHERE user_id = ?',
                    (default_city, temperature_unit, session['user_id'])
                )
            else:
                db.execute(
                    'INSERT INTO user_settings (user_id, default_city, temperature_unit) VALUES (?, ?, ?)',
                    (session['user_id'], default_city, temperature_unit)
                )
            db.commit()
            flash('Settings updated successfully', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    return render_template('profile.html', user=user, settings=settings)

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin page to manage users"""
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY id').fetchall()
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    if user_id == session['user_id']:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

# Weather routes
@app.route('/')
def home():
    """Render the home page with the weather form"""
    return render_template('index.html')

@app.route('/weather')
@login_required
def weather_api():
    """API endpoint to fetch weather data for a given city/zip (returns JSON)"""
    city = request.args.get('city')
    
    # If no city is provided, try to use the user's default city
    if not city and 'user_id' in session:
        db = get_db()
        settings = db.execute('SELECT default_city FROM user_settings WHERE user_id = ?', 
                              (session['user_id'],)).fetchone()
        if settings and settings['default_city']:
            city = settings['default_city']
    
    if not city:
        return jsonify({"error": "Please provide a city name or zip code", "error_code": "NO_CITY"}), 400
   
    try:
        url = f"https://api.weatherapi.com/v1/current.json?q={city}&key={WEATHER_API_KEY}"
        print(f"Fetching weather for: {city}")
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', 0)
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            if error_code == 1003:
                return jsonify({
                    "error": "Invalid location format. Please provide a valid city name or zip code.",
                    "error_code": "INVALID_LOCATION",
                    "api_error_code": 1003
                }), 400
            else:
                return jsonify({
                    "error": f"Weather API error: {error_message}",
                    "error_code": "API_ERROR",
                    "api_error_code": error_code
                }), response.status_code
        
        data = response.json()
        print(f"Weather data received for {city}")
        
        # Save to user's recent locations if logged in
        if 'user_id' in session:
            try:
                db = get_db()
                # Check if location already exists
                existing = db.execute(
                    'SELECT id FROM saved_locations WHERE user_id = ? AND city_name = ?',
                    (session['user_id'], city)
                ).fetchone()
                
                if existing:
                    # Update last accessed time
                    db.execute(
                        'UPDATE saved_locations SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?',
                        (existing['id'],)
                    )
                else:
                    # Only store up to 5 saved locations per user
                    count = db.execute(
                        'SELECT COUNT(*) as count FROM saved_locations WHERE user_id = ?',
                        (session['user_id'],)
                    ).fetchone()['count']
                    
                    if count >= 5:
                        # Remove oldest location
                        db.execute(
                            '''DELETE FROM saved_locations 
                               WHERE user_id = ? AND id IN (
                                   SELECT id FROM saved_locations 
                                   WHERE user_id = ? 
                                   ORDER BY last_accessed ASC 
                                   LIMIT 1
                               )''',
                            (session['user_id'], session['user_id'])
                        )
                    
                    # Insert new location
                    display_name = f"{data['location']['name']}, {data['location']['country']}"
                    db.execute(
                        'INSERT INTO saved_locations (user_id, city_name, display_name) VALUES (?, ?, ?)',
                        (session['user_id'], city, display_name)
                    )
                
                db.commit()
            except Exception as e:
                print(f"Error saving location: {e}")
        
        # Display weather in terminal
        display_terminal_weather(data)
        
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch weather data: {str(e)}", "error_code": "REQUEST_FAILED"}), 500

@app.route('/weather-display', methods=['POST'])
@login_required
def weather():
    """Renders the weather display HTML for HTMX requests with real-time updates"""
    city = request.form.get('city')
    
    # If no city is provided, try to use the user's default city
    if not city and 'user_id' in session:
        db = get_db()
        settings = db.execute('SELECT default_city FROM user_settings WHERE user_id = ?', 
                              (session['user_id'],)).fetchone()
        if settings and settings['default_city']:
            city = settings['default_city']
    
    if not city:
        return '<div class="p-4 bg-red-100 border-l-4 border-red-500 text-red-700 rounded">Please provide a city name or zip code</div>', 400
    
    try:
        url = f"https://api.weatherapi.com/v1/current.json?q={city}&key={WEATHER_API_KEY}"
        print(f"Fetching weather for: {city} (Live Update)")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            return f'<div class="p-4 bg-red-100 border-l-4 border-red-500 text-red-700 rounded">{error_message}</div>', 400
        
        weather_data = response.json()
        
        # Get user preferences for temperature unit
        temp_unit = 'celsius'
        if 'user_id' in session:
            db = get_db()
            settings = db.execute('SELECT temperature_unit FROM user_settings WHERE user_id = ?', 
                                 (session['user_id'],)).fetchone()
            if settings:
                temp_unit = settings['temperature_unit']
        
        # Save to recent locations list
        if 'user_id' in session:
            try:
                db = get_db()
                # Check if location already exists
                existing = db.execute(
                    'SELECT id FROM saved_locations WHERE user_id = ? AND city_name = ?',
                    (session['user_id'], city)
                ).fetchone()
                
                if existing:
                    # Update last accessed time
                    db.execute(
                        'UPDATE saved_locations SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?',
                        (existing['id'],)
                    )
                else:
                    # Only store up to 5 saved locations per user
                    count = db.execute(
                        'SELECT COUNT(*) as count FROM saved_locations WHERE user_id = ?',
                        (session['user_id'],)
                    ).fetchone()['count']
                    
                    if count >= 5:
                        # Remove oldest location
                        db.execute(
                            '''DELETE FROM saved_locations 
                               WHERE user_id = ? AND id IN (
                                   SELECT id FROM saved_locations 
                                   WHERE user_id = ? 
                                   ORDER BY last_accessed ASC 
                                   LIMIT 1
                               )''',
                            (session['user_id'], session['user_id'])
                        )
                    
                    # Insert new location
                    display_name = f"{weather_data['location']['name']}, {weather_data['location']['country']}"
                    db.execute(
                        'INSERT INTO saved_locations (user_id, city_name, display_name) VALUES (?, ?, ?)',
                        (session['user_id'], city, display_name)
                    )
                
                db.commit()
            except Exception as e:
                print(f"Error saving location: {e}")
        
        # Display weather in terminal
        display_terminal_weather(weather_data)
        
        # Add the current timestamp for the real-time display
        now = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Get recent locations for the user
        recent_locations = []
        if 'user_id' in session:
            try:
                db = get_db()
                recent_locations = db.execute(
                    '''SELECT * FROM saved_locations 
                       WHERE user_id = ? 
                       ORDER BY last_accessed DESC 
                       LIMIT 5''',
                    (session['user_id'],)
                ).fetchall()
            except Exception as e:
                print(f"Error getting recent locations: {e}")
        
        # Log the update for monitoring
        print(f"Live weather update for {city} at {now}")
        
        # Render the template with the weather data and current time
        return render_template('weather.html', weather=weather_data, now=now, 
                              temp_unit=temp_unit, recent_locations=recent_locations)
        
    except Exception as e:
        return f'<div class="p-4 bg-red-100 border-l-4 border-red-500 text-red-700 rounded">Error: {str(e)}</div>', 500

@app.route('/saved-locations')
@login_required
def saved_locations():
    """Display and manage saved locations"""
    db = get_db()
    locations = db.execute(
        'SELECT * FROM saved_locations WHERE user_id = ? ORDER BY last_accessed DESC',
        (session['user_id'],)
    ).fetchall()
    return render_template('saved_locations.html', locations=locations)

@app.route('/delete-location/<int:location_id>', methods=['POST'])
@login_required
def delete_location(location_id):
    """Delete a saved location"""
    db = get_db()
    db.execute(
        'DELETE FROM saved_locations WHERE id = ? AND user_id = ?',
        (location_id, session['user_id'])
    )
    db.commit()
    flash('Location deleted successfully', 'success')
    return redirect(url_for('saved_locations'))

@app.route('/set-default-city/<path:city>', methods=['POST'])
@login_required
def set_default_city(city):
    """Set a city as the default for the user"""
    db = get_db()
    settings = db.execute('SELECT * FROM user_settings WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if settings:
        db.execute(
            'UPDATE user_settings SET default_city = ? WHERE user_id = ?',
            (city, session['user_id'])
        )
    else:
        db.execute(
            'INSERT INTO user_settings (user_id, default_city) VALUES (?, ?)',
            (session['user_id'], city)
        )
    
    db.commit()
    flash(f'"{city}" set as your default city', 'success')
    return redirect(url_for('profile'))

# Initialize database before first request
@app.before_request
def before_first_request():
    init_db()

if __name__ == "__main__":
    # Display the cool weather banner
    display_weather_banner()
        
    # Print startup information
    print(f"API Key: {WEATHER_API_KEY}")
    print(f"Templates Path: {templates_dir}")
    
    # Check if template files exist
    index_path = os.path.join(templates_dir, 'index.html')
    weather_path = os.path.join(templates_dir, 'weather.html')
    login_path = os.path.join(templates_dir, 'login.html')
    register_path = os.path.join(templates_dir, 'register.html')
    profile_path = os.path.join(templates_dir, 'profile.html')
    
    for template_path, template_name in [
        (index_path, 'index.html'),
        (weather_path, 'weather.html'),
        (login_path, 'login.html'),
        (register_path, 'register.html'),
        (profile_path, 'profile.html')
    ]:
        if not os.path.exists(template_path):
            print(f"Warning: {template_name} template not found at {template_path}")
            print(f"Please create this file before running the app")
    
    # Initialize the database
    init_db()
    
    # Run the Flask app with debug mode
    print("\nStarting Flask server with LIVE UPDATES on http://127.0.0.1:5000")
    print("Weather data will automatically refresh every 60 seconds")
    print("Press CTRL+C to quit")
    app.run(debug=False)