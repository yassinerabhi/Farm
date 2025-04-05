"""
Utility module for processing sensor data
"""
import logging
import sqlite3
from typing import List, Any, Dict, Optional
from datetime import datetime
import requests
import os
from config import get_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = get_config()

def get_db_connection(device_id: str) -> sqlite3.Connection:
    """
    Get a connection to the SQLite database for a specific device
    
    Args:
        device_id (str): The unique ID of the device
        
    Returns:
        sqlite3.Connection: A connection to the SQLite database
    """
    from device_db_util import get_device_db_path
    db_path = get_device_db_path(device_id)
    return sqlite3.connect(db_path)

def validate_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize sensor data
    
    Args:
        data (dict): The sensor data to validate
        
    Returns:
        dict: The validated sensor data
    """
    validated_data = {}
    for key, value in data.items():
        # Convert non-numeric values to appropriate types
        if isinstance(value, str) and key not in ['device_id', 'wakeup_reason']:
            try:
                # Try to convert to float or int
                if '.' in value:
                    validated_data[key] = float(value)
                else:
                    validated_data[key] = int(value)
            except ValueError:
                validated_data[key] = value
        else:
            validated_data[key] = value
    
    return validated_data

def format_value(value: Any) -> Any:
    """
    Format a value for database storage
    
    Args:
        value (Any): The value to format
        
    Returns:
        Any: The formatted value
    """
    if value is None:
        return None
        
    if isinstance(value, (int, float)):
        return value
        
    if isinstance(value, str):
        return value
        
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value)
        
    return str(value)

def calculate_agricultural_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate agricultural parameters based on sensor data
    
    Args:
        data (dict): The sensor data to process
        
    Returns:
        dict: Dictionary containing calculated agricultural parameters
    """
    # Default values for calculated parameters
    params = {
        'water_stress_index': 0.0,
        'soil_fertility_index': 0.0,
        'estimated_yield': 0.0,
        'disease_risk': 0.0,
        'irrigation_recommendation': "Pas de recommandation disponible",
        'air_quality_index': 0.0,
        'evapotranspiration': 0.0,
        'vpd': 0.0,  # Vapor pressure deficit
        'gdd': 0.0,  # Growing degree days
        'soil_moisture_deficit': 0.0,
        'cwsi': 0.0,  # Crop water stress index
    }
    
    try:
        # Calculate water stress index based on soil moisture
        if 'moisture' in data:
            moisture = float(data.get('moisture', 0))
            # Assume optimal moisture is between 40% and 60%
            if moisture < 40:
                params['water_stress_index'] = (40 - moisture) / 40
            elif moisture > 60:
                params['water_stress_index'] = (moisture - 60) / 40
            else:
                params['water_stress_index'] = 0
                
            # Simple irrigation recommendation based on moisture
            if moisture < 30:
                params['irrigation_recommendation'] = "Irrigation nécessaire"
            elif moisture < 40:
                params['irrigation_recommendation'] = "Surveiller l'humidité"
            else:
                params['irrigation_recommendation'] = "Pas d'irrigation nécessaire"
                
            # Soil moisture deficit calculation
            params['soil_moisture_deficit'] = max(0, 50 - moisture)
        
        # Calculate soil fertility index based on NPK values
        n = float(data.get('nitrogen', 0))
        p = float(data.get('phosphorous', 0))
        k = float(data.get('potassium', 0))
        
        # Simple average of normalized NPK values (assuming max values of 100 for each)
        params['soil_fertility_index'] = (n + p + k) / 300
        
        # Estimated yield calculation (simplified)
        # Assume a base yield of 5 tons/hectare
        base_yield = 5.0
        # Adjust based on fertility and water stress
        fertility_factor = 1 + params['soil_fertility_index']
        water_stress_factor = 1 - params['water_stress_index']
        params['estimated_yield'] = base_yield * fertility_factor * water_stress_factor
        
        # Disease risk calculation
        # Higher risk with high humidity, moderate temperatures
        humidity = float(data.get('bme_humidity', 50))
        temperature = float(data.get('temperature', 25))
        
        # Risk increases with humidity
        humidity_factor = humidity / 100
        
        # Risk is highest around 22°C, decreases above and below that
        temp_factor = 1 - abs(temperature - 22) / 15
        temp_factor = max(0, min(1, temp_factor))
        
        params['disease_risk'] = humidity_factor * temp_factor
        
        # Air quality index (based on BME680 gas reading if available)
        if 'bme_gas' in data:
            gas = float(data.get('bme_gas', 0))
            # Higher gas resistance = better air quality
            # Assuming gas values between 0-100 (arbitrary scale)
            params['air_quality_index'] = min(1.0, gas / 100)
        
        # Vapor Pressure Deficit (VPD) calculation
        if 'temperature' in data and 'bme_humidity' in data:
            temp = float(data.get('temperature', 25))
            humidity = float(data.get('bme_humidity', 50))
            
            # Saturation vapor pressure (SVP) in kPa
            svp = 0.61078 * 10**(7.5 * temp / (237.3 + temp))
            
            # Actual vapor pressure
            avp = svp * (humidity / 100)
            
            # VPD = SVP - AVP
            params['vpd'] = svp - avp
        
        # Growing Degree Days calculation
        # Assuming a base temperature of 10°C
        if 'temperature' in data:
            temp = float(data.get('temperature', 0))
            base_temp = 10
            params['gdd'] = max(0, temp - base_temp)
        
        # Crop Water Stress Index
        # Simplified calculation based on temperature and moisture
        if 'temperature' in data and 'moisture' in data:
            temp = float(data.get('temperature', 25))
            moisture = float(data.get('moisture', 50))
            
            # Higher temperatures increase stress
            temp_factor = min(1, max(0, (temp - 15) / 25))
            
            # Lower moisture increases stress
            moisture_factor = max(0, min(1, (50 - moisture) / 50))
            
            params['cwsi'] = (temp_factor + moisture_factor) / 2
        
    except Exception as e:
        logger.error(f"Error calculating agricultural parameters: {e}")
    
    return params

def get_weather_data() -> Optional[Dict[str, Any]]:
    """
    Get current weather data from the OpenWeatherMap API
    
    Returns:
        dict: Dictionary containing weather data or None if unsuccessful
    """
    try:
        api_key = config.OPENWEATHER_API_KEY
        city = "Sfax"
        country = "Tunisia"
        
        if not api_key:
            logger.warning("OpenWeather API key not configured")
            return None
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{country}&appid={api_key}&units=metric"
        logger.info(f"Fetching weather data from: {url}")
        
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to get weather data: {response.status_code}")
            return None
        
        data = response.json()
        
        weather_data = {
            'temperature': data['main'].get('temp'),
            'humidity': data['main'].get('humidity'),
            'description': data['weather'][0].get('description') if data.get('weather') else None,
            'current_weather_description': data['weather'][0].get('main') if data.get('weather') else None,
            'current_wind_speed': data['wind'].get('speed') if data.get('wind') else None,
            'current_wind_deg': data['wind'].get('deg') if data.get('wind') else None,
            'cloudiness': data['clouds'].get('all') if data.get('clouds') else None,
            'rain': data['rain'].get('1h') if data.get('rain') else None,
            'snow': data['snow'].get('1h') if data.get('snow') else None,
            'sunrise': data['sys'].get('sunrise') if data.get('sys') else None,
            'sunset': data['sys'].get('sunset') if data.get('sys') else None
        }
        
        logger.info(f"Got weather data: {weather_data.get('temperature')}")
        return weather_data
    
    except Exception as e:
        logger.error(f"Error getting weather data: {e}")
        return None
