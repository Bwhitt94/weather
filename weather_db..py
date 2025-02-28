from db import query_db, insert_db, update_db
import datetime

# Save a location for a user
def save_location(user_id, city_name, display_name=None):
    try:
        # Set display name to city name if not provided
        if not display_name:
            display_name = city_name
            
        # Check if this location is already saved
        existing = query_db(
            'SELECT id FROM saved_locations WHERE user_id = ? AND city_name = ?',
            (user_id, city_name),
            one=True
        )
        
        if existing:
            # Update last accessed time
            update_db(
                'UPDATE saved_locations SET last_accessed = CURRENT_TIMESTAMP, display_name = ? WHERE id = ?',
                (display_name, existing['id'])
            )
            return existing['id']
        else:
            # Insert new saved location
            return insert_db(
                'INSERT INTO saved_locations (user_id, city_name, display_name) VALUES (?, ?, ?)',
                (user_id, city_name, display_name)
            )
    except Exception as e:
        print(f"Error saving location: {e}")
        return None

# Get saved locations for a user
def get_saved_locations(user_id, limit=5):
    return query_db(
        '''
        SELECT * FROM saved_locations 
        WHERE user_id = ? 
        ORDER BY last_accessed DESC 
        LIMIT ?
        ''',
        (user_id, limit)
    )

# Delete a saved location
def delete_saved_location(location_id, user_id):
    return update_db(
        'DELETE FROM saved_locations WHERE id = ? AND user_id = ?',
        (location_id, user_id)
    )