from db import query_db
from auth import register_user, authenticate_user

def test_database():
    # Test user registration
    test_user = {
        'username': 'testuser',
        'password': 'testpassword',
        'email': 'test@example.com'
    }
    
    print("Testing user registration...")
    user_id = register_user(test_user['username'], test_user['password'], test_user['email'])
    
    if user_id:
        print(f"User registered with ID: {user_id}")
    else:
        print("User already exists, trying authentication...")
    
    # Test authentication
    print("Testing user authentication...")
    user = authenticate_user(test_user['username'], test_user['password'])
    
    if user:
        print(f"Authentication successful for user: {user['username']}")
        
        # Test retrieving user settings
        settings = query_db('SELECT * FROM user_settings WHERE user_id = ?', (user['id'],), one=True)
        print(f"User settings: {dict(settings) if settings else 'No settings found'}")
    else:
        print("Authentication failed")

if __name__ == "__main__":
    test_database()