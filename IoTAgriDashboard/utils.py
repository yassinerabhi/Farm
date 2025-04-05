from functools import wraps
from flask import session, redirect, url_for, flash
from app import db
from models import Alert, SensorData

def authentication_required(f):
    """
    Decorator to check if user is logged in
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'device_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_alerts(sensor_data):
    """
    Check sensor data against thresholds and create alerts if needed
    """
    device_id = sensor_data.device_id
    alerts = []
    
    # Define thresholds
    thresholds = {
        'moisture': {'min': 20, 'max': 80, 'unit': '%'},
        'temperature': {'min': 10, 'max': 35, 'unit': '°C'},
        'ph': {'min': 5.5, 'max': 8.0, 'unit': ''},
        'ec': {'min': 500, 'max': 3000, 'unit': 'µS/cm'},
        'battery_percentage': {'min': 20, 'max': 100, 'unit': '%'}
    }
    
    # Check each parameter against thresholds
    for param, threshold in thresholds.items():
        value = getattr(sensor_data, param, None)
        
        if value is not None:
            # Check if value is below minimum threshold
            if value < threshold['min']:
                message = f"Low {param}: {value}{threshold['unit']} (below {threshold['min']}{threshold['unit']})"
                alert = Alert(
                    device_id=device_id,
                    type=param,
                    message=message,
                    level='warning'
                )
                alerts.append(alert)
            
            # Check if value is above maximum threshold
            elif value > threshold['max']:
                message = f"High {param}: {value}{threshold['unit']} (above {threshold['max']}{threshold['unit']})"
                alert = Alert(
                    device_id=device_id,
                    type=param,
                    message=message,
                    level='warning'
                )
                alerts.append(alert)
    
    # Check for extreme low battery (critical alert)
    if hasattr(sensor_data, 'battery_percentage') and sensor_data.battery_percentage is not None:
        if sensor_data.battery_percentage < 10:
            message = f"Critical battery level: {sensor_data.battery_percentage}%"
            alert = Alert(
                device_id=device_id,
                type='battery_percentage',
                message=message,
                level='danger'
            )
            alerts.append(alert)
    
    # Save alerts to database
    if alerts:
        db.session.add_all(alerts)
        db.session.commit()
    
    return alerts
