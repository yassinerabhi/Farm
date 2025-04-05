import os
import requests
from datetime import datetime
from app import db
from models import WeatherData, Device, SensorData

def get_weather_data(device_id):
    """
    Fetch weather data from OpenWeatherMap API based on device location
    """
    # Get API key from environment
    api_key = os.environ.get('OPENWEATHER_API_KEY', 'a2fb057ca6d0c40d05376d4ee8bad6ac')
    
    # Use Sfax, Tunisia as the default location as specified
    city = "Sfax"
    country = "Tunisia"
    
    # Try to get a more accurate location if available from device settings
    # Also verify that the device exists, create it if not
    device = Device.query.filter_by(id=device_id).first()
    if not device:
        # Create the device if it doesn't exist
        print(f"Creating missing device with ID: {device_id}")
        device = Device(id=device_id, name=f"Appareil {device_id}")
        db.session.add(device)
        db.session.commit()
    else:
        # In a real app, these would be attributes of the device
        city = getattr(device, 'city', city)
        country = getattr(device, 'country', country)
    
    # Make request to OpenWeatherMap API using city name
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{country}&appid={api_key}&units=metric"
    print(f"Fetching weather data from: {url}")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            # Create new weather data entry
            weather_data = WeatherData(
                device_id=device_id,
                timestamp=datetime.utcnow(),
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                wind_speed=data['wind']['speed'],
                wind_direction=data['wind']['deg'],
                weather_main=data['weather'][0]['main'],
                weather_description=data['weather'][0]['description'],
                clouds=data['clouds']['all'],
                rain_1h=data.get('rain', {}).get('1h', 0),
                rain_3h=data.get('rain', {}).get('3h', 0)
            )
            
            # Save to database
            db.session.add(weather_data)
            db.session.commit()
            
            return weather_data
        else:
            print(f"Error fetching weather data: {data.get('message', 'Unknown error')}")
            return None
    
    except Exception as e:
        print(f"Exception when fetching weather data: {e}")
        return None
