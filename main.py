from dotenv import load_dotenv
import os
from flask import Flask, render_template, jsonify, request
import requests
import time

load_dotenv()

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')


app = Flask(__name__, 
            template_folder=os.path.abspath('templates'))

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/weather')
def weather():
    city = request.args.get('city')
    if city is None:
        return "Please provide zip code.", 400
    
    url = f"https://api.weatherapi.com/v1/current.json?q={city}&key={WEATHER_API_KEY}"
    print("URL: ", url)
    response = requests.get(url)
    
    data = response.json()
    print(data)
    return jsonify(data)

def display_weather_banner():
    """Display a cool ASCII art weather banner with animation effect"""
    banner = """
    ╭──────────────────────────────────────────────────────╮
    │                                                      │
    │   ☁️  ☀️  🌦️  WEATHER FORECAST API 🌧️  ❄️  🌈      │
    │                                                      │
    │   ┌───────────────┐        ┌─────────────────────┐  │
    │   │  TEMPERATURE  │        │  POWERED BY WEATHER │  │
    │   │    ° F│° C    │◀──────▶│        API          │  │
    │   └───────────────┘        └─────────────────────┘  │
    │                                                      │
    │         CITY SEARCH & REAL-TIME FORECASTS           │
    │                                                      │
    ╰──────────────────────────────────────────────────────╯
    """
    
    # For simple animation effect
    # os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    # Print the banner character by character with a slight delay
    for char in banner:
        print(char, end='', flush=True)
        #time.sleep(0.001)  # Small delay for visual effect
    
    print("\n")  # Add some space after the banner

    
if __name__ == "__main__":
      # Create templates directory if it doesn't exist
     
    print("Key: ", WEATHER_API_KEY)
    print("Templates Path: ", os.path.abspath('templates'))

     
    display_weather_banner()
      
    templates_dir = os.path.abspath('templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        print(f"Created templates directory at: {templates_dir}")
    
    # Check if index.html exists
    index_path = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_path):
        print(f"Warning: index.html template not found at {index_path}")
        print("Please create this file before running the app")
    
    app.run()