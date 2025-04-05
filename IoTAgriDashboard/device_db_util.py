"""
Utility module for managing device-specific databases
"""
import os
import sqlite3
from datetime import datetime
import json
import logging

from flask import current_app

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
DEVICE_DB_FOLDER = 'device_databases'
ATTACHED_ASSETS_FOLDER = 'attached_assets'

def ensure_device_db_folder():
    """Ensure the device database folder exists"""
    if not os.path.exists(DEVICE_DB_FOLDER):
        os.makedirs(DEVICE_DB_FOLDER)
        logger.info(f"Created device database folder: {DEVICE_DB_FOLDER}")

def get_device_db_path(device_id):
    """
    Get the path to a device-specific database
    First checks the device_databases folder, then the attached_assets folder
    """
    ensure_device_db_folder()
    
    # Check in the device_databases folder first
    db_path = os.path.join(DEVICE_DB_FOLDER, f"{device_id}.db")
    if os.path.exists(db_path):
        return db_path
    
    # Check in the attached_assets folder
    attached_db_path = os.path.join(ATTACHED_ASSETS_FOLDER, f"{device_id}.db")
    if os.path.exists(attached_db_path):
        # Copy the database to the device_databases folder
        import shutil
        shutil.copy2(attached_db_path, db_path)
        logger.info(f"Copied database from {attached_db_path} to {db_path}")
        return db_path
    
    # If the database doesn't exist, create it
    create_device_database(device_id)
    return db_path

def create_device_database(device_id):
    """Create a new device-specific database with the necessary tables"""
    db_path = os.path.join(DEVICE_DB_FOLDER, f"{device_id}.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create SENSOR_DATA table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SENSOR_DATA (
        id INTEGER PRIMARY KEY,
        Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        battv REAL,
        battpc REAL,
        MOISTURE REAL,
        TEMPERATURE REAL,
        EC REAL,
        PH REAL,
        NITROGEN REAL,
        PHOSPHOROUS REAL,
        POTASSIUM REAL,
        SALINITY REAL,
        BME_TEMPERATURE REAL,
        BME_HUMIDITY REAL,
        BME_PRESSURE REAL,
        BME_GAS REAL,
        UV_INDEX REAL,
        pluie REAL,
        wakeup_reason TEXT,
        water_stress_index REAL,
        soil_fertility_index REAL,
        estimated_yield REAL,
        disease_risk REAL,
        irrigation_recommendation TEXT,
        air_quality_index REAL,
        evapotranspiration REAL,
        vpd REAL,
        gdd REAL,
        soil_moisture_deficit REAL,
        cwsi REAL,
        weather_temperature REAL,
        weather_humidity REAL,
        weather_description TEXT,
        current_weather_description TEXT,
        current_wind_speed REAL,
        current_wind_deg INTEGER,
        cloudiness INTEGER,
        rain REAL,
        snow REAL,
        sunrise INTEGER,
        sunset INTEGER,
        SODIUM REAL,
        CALCIUM REAL,
        MAGNESIUM REAL,
        CEC REAL,
        ORGANIC_MATTER REAL,
        CLAY_CONTENT REAL
    )
    ''')
    
    # Create CONVERSATION_HISTORY table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS CONVERSATION_HISTORY (
        id INTEGER PRIMARY KEY,
        user_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_message TEXT,
        assistant_response TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info(f"Created device database for {device_id}")
    return db_path

def store_sensor_data_in_device_db(device_id, data):
    """
    Store sensor data in the device-specific database
    
    Args:
        device_id (str): The unique ID of the device
        data (dict): The sensor data to store
    """
    db_path = get_device_db_path(device_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get column names from the SENSOR_DATA table
    cursor.execute("PRAGMA table_info(SENSOR_DATA)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Convert the data keys to match the database columns
    insert_data = {}
    for key, value in data.items():
        # Convert camelCase or lowercase to uppercase
        db_key = key.upper() if key.upper() in columns else key
        if db_key in columns:
            insert_data[db_key] = value
    
    # Special handling for timestamp
    insert_data['Time'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    # Build the SQL query
    columns_str = ', '.join(insert_data.keys())
    placeholders = ', '.join(['?' for _ in insert_data])
    values = tuple(insert_data.values())
    
    query = f"INSERT INTO SENSOR_DATA ({columns_str}) VALUES ({placeholders})"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        logger.info(f"Inserted sensor data into device database for {device_id}")
    except Exception as e:
        logger.error(f"Error inserting data into device database: {e}")
    finally:
        conn.close()

def get_sensor_data_from_device_db(device_id, limit=50, from_date=None, to_date=None):
    """
    Get sensor data from the device-specific database
    
    Args:
        device_id (str): The unique ID of the device
        limit (int): The maximum number of records to retrieve
        from_date (str): Start date in format 'YYYY-MM-DD'
        to_date (str): End date in format 'YYYY-MM-DD'
        
    Returns:
        list: A list of dictionaries containing the sensor data
    """
    db_path = get_device_db_path(device_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM SENSOR_DATA"
        params = []
        
        print(f"Getting data with filter params: from_date={from_date}, to_date={to_date}, limit={limit}")
        
        # Add date filters if provided
        if from_date or to_date:
            if from_date and to_date:
                query += " WHERE Time >= ? AND Time <= ?"
                # Add time to make it the end of the day
                to_date_with_time = to_date + " 23:59:59"
                params.extend([from_date, to_date_with_time])
                print(f"Using date range filter: {from_date} to {to_date_with_time}")
            elif from_date:
                query += " WHERE Time >= ?"
                params.append(from_date)
                print(f"Using from_date filter: {from_date}")
            elif to_date:
                query += " WHERE Time <= ?"
                # Add time to make it the end of the day
                to_date_with_time = to_date + " 23:59:59"
                params.append(to_date_with_time)
                print(f"Using to_date filter: {to_date_with_time}")
        
        # Add order and limit
        query += " ORDER BY Time DESC LIMIT ?"
        params.append(limit)
        
        print(f"Final SQL query: {query} with params {params}")
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        # Convert rows to a list of dictionaries
        result = []
        for row in rows:
            row_dict = {k: row[k] for k in row.keys()}
            result.append(row_dict)
            
        return result
    except Exception as e:
        logger.error(f"Error retrieving data from device database: {e}")
        return []
    finally:
        conn.close()

def store_conversation_in_device_db(device_id, user_id, user_message, assistant_response):
    """
    Store a conversation in the device-specific database
    
    Args:
        device_id (str): The unique ID of the device
        user_id (str): The user ID or identifier
        user_message (str): The message sent by the user
        assistant_response (str): The response from the assistant
    """
    db_path = get_device_db_path(device_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO CONVERSATION_HISTORY (user_id, user_message, assistant_response) VALUES (?, ?, ?)",
            (user_id, user_message, assistant_response)
        )
        conn.commit()
        logger.info(f"Stored conversation in device database for {device_id}")
    except Exception as e:
        logger.error(f"Error storing conversation in device database: {e}")
    finally:
        conn.close()

def get_conversation_history_from_device_db(device_id, limit=20):
    """
    Get conversation history from the device-specific database
    
    Args:
        device_id (str): The unique ID of the device
        limit (int): The maximum number of records to retrieve
        
    Returns:
        list: A list of dictionaries containing the conversation history
    """
    db_path = get_device_db_path(device_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM CONVERSATION_HISTORY ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        # Convert rows to a list of dictionaries
        result = []
        for row in rows:
            row_dict = {k: row[k] for k in row.keys()}
            result.append(row_dict)
            
        return result
    except Exception as e:
        logger.error(f"Error retrieving conversation history from device database: {e}")
        return []
    finally:
        conn.close()