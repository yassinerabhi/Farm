from flask import request, jsonify, Blueprint, session
from app import db
from models import SensorData, Device
from datetime import datetime
import os
import importlib
import logging
import sqlite3
from typing import List, Any
from utils import check_alerts
from device_db_util import store_sensor_data_in_device_db, get_sensor_data_from_device_db
from data_processing import (
    get_db_connection, 
    validate_sensor_data, 
    format_value, 
    calculate_agricultural_parameters,
    get_weather_data
)
from anomaly_detection import detect_anomalies, train_models_for_all_devices, train_anomaly_detection_model

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__)

@api_bp.route('/data', methods=['POST'])
def receive_sensor_data():
    """
    Endpoint to receive sensor data from IoT devices
    """
    logger.info("Received POST request to /data")
    if not request.is_json:
        logger.error("Request is not JSON")
        return jsonify(error="La requête doit être en format JSON. 😕"), 400

    try:
        content = request.json
        logger.info(f"Received JSON content: {content}")

        device_id = content.get('device_id')
        if not device_id:
            logger.error("device_id is missing in the JSON payload")
            return jsonify(error="L'ID de l'appareil est requis. Vous l'avez oublié ? 🤔"), 400

        logger.info(f"Processing data for device {device_id}")

        # Validate and process data
        validated_content = validate_sensor_data(content)
        
        # Store data in the database
        conn = get_db_connection(device_id)
        cursor = conn.cursor()

        # Calculate additional agricultural parameters
        agri_params = calculate_agricultural_parameters(validated_content)

        # Get current weather data
        weather_data = get_weather_data()

        # Format all values for database storage
        formatted_values = tuple(format_value(v) for v in [
            content.get('battv', 0.0),
            content.get('battpc', 0),
            content.get('moisture', 0.0),
            content.get('temperature', 0.0),
            content.get('ec', 0),            
            content.get('ph', 0.0),
            content.get('nitrogen', 0),
            content.get('phosphorous', 0),
            content.get('potassium', 0),
            content.get('salinity', 0.0),
            content.get('bme_temperature', 0.0),
            content.get('bme_humidity', 0.0),
            content.get('bme_pressure', 0.0),
            content.get('bme_gas', 0.0),
            content.get('uv_index', 0.0),
            content.get('pluie', 0),
            content.get('wakeup_reason', ''),
            agri_params['water_stress_index'],
            agri_params['soil_fertility_index'],
            agri_params['estimated_yield'],
            agri_params['disease_risk'],
            agri_params['irrigation_recommendation'],
            agri_params['air_quality_index'],
            agri_params['evapotranspiration'],
            agri_params['vpd'],
            agri_params['gdd'],
            agri_params['soil_moisture_deficit'],
            agri_params['cwsi'],
            weather_data['temperature'] if weather_data else None,
            weather_data['humidity'] if weather_data else None,
            weather_data['description'] if weather_data else None,
            weather_data['current_weather_description'] if weather_data else None,
            weather_data['current_wind_speed'] if weather_data else None,
            weather_data['current_wind_deg'] if weather_data else None,
            weather_data['cloudiness'] if weather_data else None,
            weather_data['rain'] if weather_data else None,
            weather_data['snow'] if weather_data else None,
            weather_data['sunrise'] if weather_data else None,
            weather_data['sunset'] if weather_data else None,
            content.get('sodium', 0.0),
            content.get('calcium', 0.0),
            content.get('magnesium', 0.0),
            content.get('cec', 0.0),
            content.get('organic_matter', 0.0),
            content.get('clay_content', 0.0)
        ])

        # Insert data into the device-specific database
        cursor.execute("""
            INSERT INTO SENSOR_DATA (
                battv, battpc, MOISTURE, TEMPERATURE, EC, PH, NITROGEN, PHOSPHOROUS, POTASSIUM, SALINITY, 
                BME_TEMPERATURE, BME_HUMIDITY, BME_PRESSURE, BME_GAS, UV_INDEX, pluie, wakeup_reason,
                water_stress_index, soil_fertility_index, estimated_yield, disease_risk, irrigation_recommendation,
                air_quality_index, evapotranspiration, vpd, gdd, soil_moisture_deficit, cwsi,
                weather_temperature, weather_humidity, weather_description,
                current_weather_description, current_wind_speed, current_wind_deg, cloudiness, rain, snow, sunrise, sunset,
                SODIUM, CALCIUM, MAGNESIUM, CEC, ORGANIC_MATTER, CLAY_CONTENT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, formatted_values)

        conn.commit()
        conn.close()

        logger.info(f"Data successfully inserted for device {device_id}")
        
        # Also process with main system
        process_sensor_data(content)

        return jsonify(message='Données reçues et enregistrées avec succès ! 🎉'), 200
    except Exception as e:
        logger.error(f"Error in data route: {str(e)}")
        return jsonify(error=f"Oups ! Une erreur s'est produite : {str(e)}. On réessaie ? 🔄"), 500

@api_bp.route('/device/<device_id>/data', methods=['GET'])
def get_device_data(device_id):
    """
    Endpoint to get device-specific sensor data
    """
    try:
        # Essayons différentes façons de récupérer les paramètres
        # 1. Récupération directe de l'URL
        url = request.url
        logger.info(f"Full request URL: {url}")
        
        # 2. Récupération détaillée de tous les arguments
        all_args = dict(request.args)
        logger.info(f"All request args: {all_args}")
        
        # Récupération des paramètres spécifiques
        limit = request.args.get('limit', default=50, type=int)
        
        # Analyse manuelle de l'URL pour extraire les paramètres 'from' et 'to'
        from_date = None
        to_date = None
        
        if '?from=' in url:
            start_idx = url.index('?from=') + 6
            end_idx = url.index('&', start_idx) if '&' in url[start_idx:] else len(url)
            from_date = url[start_idx:end_idx]
            logger.info(f"Extracted from_date={from_date} manually from URL")
            
        if '&to=' in url:
            start_idx = url.index('&to=') + 4
            end_idx = url.index('&', start_idx) if '&' in url[start_idx:] else len(url)
            to_date = url[start_idx:end_idx]
            logger.info(f"Extracted to_date={to_date} manually from URL")
        
        # Log the request parameters
        logger.info(f"Device data request processed: device_id={device_id}, from={from_date}, to={to_date}, limit={limit}")
        
        # Get data from device-specific database with date filters
        data = get_sensor_data_from_device_db(
            device_id, 
            limit=limit,
            from_date=from_date,
            to_date=to_date
        )
        
        # Return the data
        return jsonify({
            "success": True,
            "device_id": device_id,
            "count": len(data),
            "data": data,
            "filters": {
                "from": from_date,
                "to": to_date,
                "limit": limit
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting device data: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/get_sensor_data/<device_id>', methods=['GET'])
def get_sensor_data(device_id):
    """
    Endpoint to get sensor data for a specific device in a structured format
    """
    logger.info(f"Received GET request for sensor data of device {device_id}")
    try:
        conn = get_db_connection(device_id)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='SENSOR_DATA'")
        if not cursor.fetchone():
            conn.close()
            return jsonify(message="En attente de données du capteur"), 200

        cursor.execute("SELECT * FROM SENSOR_DATA ORDER BY Time DESC")
        data = cursor.fetchall()
        conn.close()

        if not data:
            return jsonify(message="En attente de données du capteur"), 200

        formatted_data = format_sensor_data(data)

        logger.info(f"Successfully retrieved and formatted data for device {device_id}")
        return jsonify(formatted_data)
    except Exception as e:
        logger.error(f"Error in get_sensor_data route for device {device_id}: {str(e)}")
        return jsonify(error=str(e)), 500
        
# Helper function for formatting sensor data
def format_sensor_data(data: List[sqlite3.Row]) -> List[List[Any]]:
    """Format sensor data for the API response"""
    formatted_data = []
    for row in data:
        formatted_row = list(row)
        if isinstance(formatted_row[1], str):
            try:
                dt = datetime.strptime(formatted_row[1], '%Y-%m-%d %H:%M:%S')
                formatted_row[1] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        elif isinstance(formatted_row[1], datetime):
            formatted_row[1] = formatted_row[1].strftime('%Y-%m-%d %H:%M:%S')

        formatted_row[2:] = [format_value(val) for val in formatted_row[2:]]
        formatted_data.append(formatted_row)
    return formatted_data

@api_bp.route('/test', methods=['GET'])
def test_api():
    """
    Test endpoint to verify API is working
    """
    return jsonify({
        "success": True,
        "message": "API is working correctly",
        "version": "1.0.0"
    }), 200

@api_bp.route('/train-anomaly-models', methods=['POST'])
def train_anomaly_models():
    """
    Endpoint to train anomaly detection models for the selected parameters
    """
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid request format"}), 400
    
    data = request.json
    parameters = data.get('parameters', [])
    
    if not parameters:
        return jsonify({"success": False, "error": "No parameters selected"}), 400
    
    logger.info(f"Training anomaly detection models for parameters: {parameters}")
    
    try:
        # Get device IDs
        devices = Device.query.all()
        device_ids = [device.id for device in devices]
        
        results = {
            'success': [],
            'failed': []
        }
        
        # Train models for each device and parameter
        for device_id in device_ids:
            for param in parameters:
                model, scaler = train_anomaly_detection_model(device_id, param)
                if model is not None and scaler is not None:
                    results['success'].append(f"{device_id}/{param}")
                else:
                    results['failed'].append(f"{device_id}/{param}")
        
        message = f"Formation terminée. {len(results['success'])} modèles formés avec succès. {len(results['failed'])} échecs."
        logger.info(message)
        
        return jsonify({
            "success": True,
            "message": message,
            "results": results
        }), 200
    except Exception as e:
        logger.error(f"Error training anomaly models: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/train-all-anomaly-models', methods=['POST'])
def train_all_anomaly_models():
    """
    Endpoint to train anomaly detection models for all devices and parameters
    """
    try:
        logger.info("Training all anomaly detection models")
        results = train_models_for_all_devices()
        
        message = f"Formation terminée. {len(results['success'])} modèles formés avec succès. {len(results['failed'])} échecs."
        logger.info(message)
        
        return jsonify({
            "success": True,
            "message": message,
            "results": results
        }), 200
    except Exception as e:
        logger.error(f"Error training all anomaly models: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/anomalies/<device_id>', methods=['GET'])
def get_anomalies(device_id):
    """
    Endpoint to get anomaly alerts for a specific device
    """
    try:
        from models import Alert
        
        # Get anomaly alerts for the device
        alerts = Alert.query.filter_by(
            device_id=device_id
        ).order_by(
            Alert.timestamp.desc()
        ).all()
        
        # Format alerts
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                'id': alert.id,
                'type': alert.type,
                'message': alert.message,
                'level': alert.level,
                'timestamp': alert.timestamp.isoformat(),
                'acknowledged': alert.acknowledged
            })
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'count': len(formatted_alerts),
            'alerts': formatted_alerts
        }), 200
    except Exception as e:
        logger.error(f"Error getting anomalies for device {device_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/acknowledge-alert/<int:alert_id>', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    Endpoint to acknowledge an alert
    """
    try:
        from models import Alert
        
        # Find the alert
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        # Acknowledge the alert
        alert.acknowledged = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alert acknowledged'
        }), 200
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def process_sensor_data(data):
    """
    Process and store sensor data received from the IoT device
    """
    # Extract data from the request
    device_id = data.get('device_id')
    if not device_id:
        logger.error("No device_id provided in sensor data")
        raise ValueError("No device_id provided in sensor data")
    
    logger.info(f"Processing sensor data for device: {device_id}")
    
    # Check if device exists, create it if not
    device = Device.query.filter_by(id=device_id).first()
    if not device:
        logger.info(f"Creating new device with ID: {device_id}")
        device = Device(id=device_id, name=f"Appareil {device_id}")
        db.session.add(device)
        db.session.commit()
    
    # Update last_seen timestamp
    device.last_seen = datetime.utcnow()
    db.session.commit()
    
    # Store data in device-specific database
    try:
        logger.info(f"Storing data in device-specific database for device: {device_id}")
        store_sensor_data_in_device_db(device_id, data)
    except Exception as e:
        logger.error(f"Error storing data in device-specific database: {e}")
    
    # Create a new sensor data entry in the main database
    sensor_data = SensorData(
        device_id=device_id,
        timestamp=datetime.utcnow(),
        
        # Basic sensor data
        moisture=data.get('moisture'),
        temperature=data.get('temperature'),
        ec=data.get('ec'),
        ph=data.get('ph'),
        
        # Nutrient data
        nitrogen=data.get('nitrogen'),
        phosphorous=data.get('phosphorous'),
        potassium=data.get('potassium'),
        salinity=data.get('salinity'),
        
        # Environmental data
        bme_temperature=data.get('bme_temperature'),
        bme_humidity=data.get('bme_humidity'),
        bme_pressure=data.get('bme_pressure'),
        bme_gas=data.get('bme_gas'),
        uv_index=data.get('uv_index'),
        
        # Extract rain level from pluie field (renamed from average in the Arduino code)
        rain_level=data.get('pluie'),
        
        # Battery info
        battery_voltage=data.get('battv'),
        battery_percentage=data.get('battpc'),
        
        # Wake-up reason
        wakeup_reason=data.get('wakeup_reason')
    )
    
    # Save to main database
    db.session.add(sensor_data)
    db.session.commit()
    logger.info(f"Saved sensor data to main database, ID: {sensor_data.id}")
    
    # Check sensor values against thresholds and create alerts if needed
    try:
        check_alerts(sensor_data)
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
    
    # Perform anomaly detection on sensor data
    try:
        # Get language for user interface from session or default to French
        lang = session.get('language', 'fr') if 'language' in session else 'fr'
        
        # Detect anomalies using ML models
        logger.info(f"Performing anomaly detection for device: {device_id}")
        anomalies = detect_anomalies(device_id, data, lang)
        
        if anomalies:
            logger.info(f"Detected {len(anomalies)} anomalies in sensor data for device {device_id}")
            for anomaly in anomalies:
                logger.info(f"Anomaly detected: {anomaly['parameter_name']} = {anomaly['value']} (score: {anomaly['score']:.4f})")
    except Exception as e:
        logger.error(f"Error during anomaly detection: {e}")
    
    # Trigger weather data update and AI analysis if possible
    try:
        # Import here to avoid circular imports
        from weather import get_weather_data
        from ai import get_ai_analysis
        
        # Get weather data for the device location
        get_weather_data(device_id)
        
        # Generate AI analysis for the new data
        get_ai_analysis(device_id)
    except Exception as e:
        logger.error(f"Error triggering additional processing: {e}")
    
    return sensor_data
