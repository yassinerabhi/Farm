from flask import render_template, redirect, url_for, session, request, jsonify, flash, send_file
from models import Device, SensorData, Alert, WeatherData, AIAnalysis, Report
from app import db
from datetime import datetime, timedelta
import json
import os
import logging

from api import process_sensor_data
from weather import get_weather_data
from ai import get_ai_analysis
from report import generate_pdf_report
from utils import check_alerts, authentication_required
from anomaly_detection import detect_anomalies, train_models_for_all_devices

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def register_routes(app):
    # Authentication routes
    @app.route('/')
    def index():
        if 'device_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            device_id = request.form.get('device_id')
            # Check if device exists
            device = Device.query.filter_by(id=device_id).first()
            
            if not device:
                # First time login for this device, create a record
                device = Device(id=device_id)
                db.session.add(device)
                db.session.commit()
                flash(f'Device {device_id} registered successfully.', 'success')
            
            # Update last seen timestamp
            device.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Set session
            session['device_id'] = device_id
            return redirect(url_for('dashboard'))
        
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('device_id', None)
        return redirect(url_for('login'))

    # Dashboard routes
    @app.route('/dashboard')
    @authentication_required
    def dashboard():
        device_id = session.get('device_id')
        
        # Get the latest sensor data
        latest_data = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
        
        # Get the latest weather data
        weather = WeatherData.query.filter_by(device_id=device_id).order_by(WeatherData.timestamp.desc()).first()
        
        # Get the latest AI analysis
        analysis = AIAnalysis.query.filter_by(device_id=device_id).order_by(AIAnalysis.timestamp.desc()).first()
        
        # Get recent alerts
        alerts = Alert.query.filter_by(device_id=device_id, acknowledged=False).order_by(Alert.timestamp.desc()).limit(5).all()
        
        return render_template('dashboard.html', 
                            sensor_data=latest_data, 
                            weather=weather, 
                            analysis=analysis, 
                            alerts=alerts,
                            device_id=device_id)

    @app.route('/history')
    @authentication_required
    def history():
        device_id = session.get('device_id')
        
        # Default to last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        # Get time range from query parameters if provided
        period = request.args.get('period', '1d')
        
        if period == '1w':
            start_date = end_date - timedelta(days=7)
        elif period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
            
        # Try to get custom date range from query parameters
        custom_start = request.args.get('start')
        custom_end = request.args.get('end')
        
        if custom_start and custom_end:
            try:
                start_date = datetime.fromisoformat(custom_start)
                end_date = datetime.fromisoformat(custom_end + 'T23:59:59')  # Include the full end day
            except ValueError:
                flash('Invalid date format', 'error')
        
        # Get historical data from device-specific database
        from device_db_util import get_sensor_data_from_device_db
        device_data = get_sensor_data_from_device_db(device_id, limit=1000)
        
        # Filter data based on the selected date range
        # Convert device_data timestamps to datetime objects for comparison
        filtered_data = []
        for entry in device_data:
            # Convert timestamp string to datetime object
            try:
                entry_time = datetime.fromisoformat(entry.get('Time'))
                # Check if the entry is within the selected date range
                if start_date <= entry_time <= end_date:
                    # Create a compatible object structure for the template
                    sensor_entry = type('SensorDataObj', (), {
                        'timestamp': entry_time,
                        'moisture': entry.get('MOISTURE'),
                        'temperature': entry.get('TEMPERATURE'),
                        'ph': entry.get('PH'),
                        'ec': entry.get('EC'),
                        'nitrogen': entry.get('NITROGEN'),
                        'phosphorous': entry.get('PHOSPHOROUS'),
                        'potassium': entry.get('POTASSIUM'),
                        'bme_temperature': entry.get('BME_TEMPERATURE'),
                        'bme_humidity': entry.get('BME_HUMIDITY'),
                        'bme_pressure': entry.get('BME_PRESSURE'),
                        'uv_index': entry.get('UV_INDEX'),
                        'rain_level': entry.get('pluie'),
                        'battery_voltage': entry.get('battv'),
                        'battery_percentage': entry.get('battpc')
                    })
                    filtered_data.append(sensor_entry)
            except (ValueError, TypeError) as e:
                print(f"Error processing entry timestamp: {e}")
                continue
        
        # Sort data by timestamp
        filtered_data.sort(key=lambda x: x.timestamp)
        
        return render_template('history.html', 
                            data=filtered_data, 
                            period=period, 
                            start_date=start_date, 
                            end_date=end_date,
                            device_id=device_id)

    @app.route('/reports')
    @authentication_required
    def reports():
        device_id = session.get('device_id')
        
        # Get all reports for this device
        reports = Report.query.filter_by(device_id=device_id).order_by(Report.created_at.desc()).all()
        
        return render_template('reports.html', 
                            reports=reports,
                            device_id=device_id)

    @app.route('/weather')
    @authentication_required
    def weather():
        device_id = session.get('device_id')
        
        # Get the latest weather data
        weather_data = WeatherData.query.filter_by(device_id=device_id).order_by(WeatherData.timestamp.desc()).first()
        
        # Always fetch new weather data for debugging purposes
        try:
            print(f"Attempting to fetch weather data for device {device_id}")
            weather_data = get_weather_data(device_id)
        except Exception as e:
            print(f"Exception when getting weather data: {e}")
        
        # Log for debugging
        if weather_data:
            print(f"Got weather data: {weather_data.id}")
        else:
            print("Failed to get weather data")
            
        return render_template('weather.html', 
                            weather=weather_data,
                            device_id=device_id)

    @app.route('/settings')
    @authentication_required
    def settings():
        device_id = session.get('device_id')
        
        # Get device information
        device = Device.query.filter_by(id=device_id).first()
        
        return render_template('settings.html', 
                            device=device,
                            device_id=device_id)

    # Device data visualization
    @app.route('/device/<device_id>/data')
    @authentication_required
    def device_data(device_id):
        # Check if requested device_id matches the logged-in device
        if session.get('device_id') != device_id:
            flash('You can only view data for your own device.', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('device_data.html', device_id=device_id)

    # API routes
    @app.route('/api/sensor-data', methods=['POST'])
    def sensor_data():
        # Process incoming sensor data from Arduino
        data = request.json
        
        if not data or 'device_id' not in data:
            return jsonify({'error': 'Invalid data format'}), 400
        
        # Process and store sensor data
        sensor_data = process_sensor_data(data)
        
        # Check for alerts
        check_alerts(sensor_data)
        
        # Trigger weather data update
        try:
            get_weather_data(data['device_id'])
        except Exception as e:
            print(f"Error updating weather data: {e}")
        
        # Trigger AI analysis if we have enough data
        try:
            recent_count = SensorData.query.filter_by(device_id=data['device_id']).count()
            if recent_count > 5:  # Only trigger analysis if we have some history
                # Use the default language (French) for automatic analyses
                get_ai_analysis(data['device_id'], language='fr')
        except Exception as e:
            print(f"Error generating AI analysis: {e}")
        
        return jsonify({'success': True}), 200

    @app.route('/api/generate-report', methods=['POST'])
    @authentication_required
    def generate_report():
        device_id = session.get('device_id')
        data = request.json
        
        # Extract report parameters
        title = data.get('title', f'Report {datetime.now().strftime("%Y-%m-%d")}')
        start_date = datetime.fromisoformat(data.get('start_date'))
        end_date = datetime.fromisoformat(data.get('end_date'))
        
        # Generate PDF report
        report_path = generate_pdf_report(device_id, title, start_date, end_date)
        
        # Store report information
        report = Report(
            device_id=device_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
            file_path=report_path
        )
        db.session.add(report)
        db.session.commit()
        
        return jsonify({'success': True, 'report_id': report.id}), 200

    @app.route('/api/download-report/<int:report_id>')
    @authentication_required
    def download_report(report_id):
        device_id = session.get('device_id')
        
        # Get report information
        report = Report.query.filter_by(id=report_id, device_id=device_id).first()
        
        if not report:
            flash('Report not found.', 'error')
            return redirect(url_for('reports'))
        
        # Send file for download
        return send_file(report.file_path, as_attachment=True, download_name=f"{report.title}.pdf")

    @app.route('/api/update-device', methods=['POST'])
    @authentication_required
    def update_device():
        device_id = session.get('device_id')
        data = request.json
        
        # Get device information
        device = Device.query.filter_by(id=device_id).first()
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Update device name
        if 'name' in data:
            device.name = data['name']
            db.session.commit()
        
        return jsonify({'success': True}), 200

    @app.route('/api/acknowledge-alert/<int:alert_id>', methods=['POST'])
    @authentication_required
    def acknowledge_alert(alert_id):
        device_id = session.get('device_id')
        
        # Get the alert
        alert = Alert.query.filter_by(id=alert_id, device_id=device_id).first()
        
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        # Mark as acknowledged
        alert.acknowledged = True
        db.session.commit()
        
        return jsonify({'success': True}), 200

    # Data API endpoints for charts
    @app.route('/api/chart-data')
    @authentication_required
    def chart_data():
        device_id = session.get('device_id')
        
        # Get parameters
        param = request.args.get('param', 'temperature')
        period = request.args.get('period', '1d')
        
        # Set time range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        if period == '1w':
            start_date = end_date - timedelta(days=7)
        elif period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        
        # Get historical data from device-specific database
        from device_db_util import get_sensor_data_from_device_db
        device_data = get_sensor_data_from_device_db(device_id, limit=1000)
        
        # Filter data based on the selected date range and parameter
        filtered_data = []
        for entry in device_data:
            try:
                entry_time = datetime.fromisoformat(entry.get('Time'))
                if start_date <= entry_time <= end_date:
                    filtered_data.append({
                        'timestamp': entry_time,
                        'value': get_value_from_entry(entry, param)
                    })
            except (ValueError, TypeError) as e:
                print(f"Error processing entry: {e}")
                continue
        
        # Sort data by timestamp
        filtered_data.sort(key=lambda x: x['timestamp'])
        
        # Format data for chart.js
        labels = [entry['timestamp'].strftime('%Y-%m-%d %H:%M') for entry in filtered_data]
        values = [entry['value'] for entry in filtered_data]
        
        return jsonify({
            'labels': labels,
            'values': values,
            'param': param
        })
        
    # Helper function to get values from device data entries
    def get_value_from_entry(entry, param):
        # Map parameter names to device database field names
        param_map = {
            'temperature': 'TEMPERATURE',
            'moisture': 'MOISTURE',
            'ph': 'PH',
            'ec': 'EC',
            'nitrogen': 'NITROGEN',
            'phosphorous': 'PHOSPHOROUS',
            'potassium': 'POTASSIUM',
            'bme_temperature': 'BME_TEMPERATURE',
            'bme_humidity': 'BME_HUMIDITY',
            'bme_pressure': 'BME_PRESSURE',
            'uv_index': 'UV_INDEX',
            'rain_level': 'pluie',
            'battery_voltage': 'battv',
            'battery_percentage': 'battpc'
        }
        
        field_name = param_map.get(param, param)
        return entry.get(field_name)

    @app.route('/api/recent-data')
    @authentication_required
    def recent_data():
        device_id = session.get('device_id')
        
        # Get latest data point
        latest = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
        
        if not latest:
            return jsonify({'error': 'No data available'}), 404
        
        # Convert to dict
        data = {
            'timestamp': latest.timestamp.isoformat(),
            'moisture': latest.moisture,
            'temperature': latest.temperature,
            'ec': latest.ec,
            'ph': latest.ph,
            'nitrogen': latest.nitrogen,
            'phosphorous': latest.phosphorous,
            'potassium': latest.potassium,
            'salinity': latest.salinity,
            'bme_temperature': latest.bme_temperature,
            'bme_humidity': latest.bme_humidity,
            'bme_pressure': latest.bme_pressure,
            'bme_gas': latest.bme_gas,
            'uv_index': latest.uv_index,
            'rain_level': latest.rain_level,
            'battery_voltage': latest.battery_voltage,
            'battery_percentage': latest.battery_percentage
        }
        
        return jsonify(data)

    # Anomaly Detection route
    @app.route('/anomalies')
    @authentication_required
    def anomalies():
        device_id = session.get('device_id')
        
        # Get recent anomaly alerts
        anomaly_alerts = Alert.query.filter_by(
            device_id=device_id
        ).filter(
            Alert.message.like('%Anomalie%')
        ).order_by(Alert.timestamp.desc()).limit(20).all()
        
        # Get sensor data for training or visualization
        latest_data = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
        
        return render_template('anomalies.html', 
                            anomaly_alerts=anomaly_alerts,
                            latest_data=latest_data,
                            device_id=device_id)
                            
    # Train anomaly detection models route
    @app.route('/api/train-anomaly-models', methods=['POST'])
    @authentication_required
    def train_anomaly_models():
        device_id = session.get('device_id')
        
        # Start training in background (would normally use a task queue for this)
        try:
            logger.info(f"Starting anomaly detection model training for device {device_id}")
            if device_id:
                # Train models for the specific sensor parameters
                sensor_params = request.json.get('parameters', [
                    'temperature', 'moisture', 'ph', 'ec', 
                    'nitrogen', 'phosphorous', 'potassium'
                ])
                
                results = {}
                for param in sensor_params:
                    from anomaly_detection import train_anomaly_detection_model
                    model, scaler = train_anomaly_detection_model(device_id, param)
                    results[param] = model is not None and scaler is not None
                
                return jsonify({
                    'success': True,
                    'message': f'Modèles de détection d\'anomalies entraînés pour {len(results)} paramètres.',
                    'results': results
                })
            else:
                # Train models for all registered devices
                train_models_for_all_devices()
                return jsonify({
                    'success': True,
                    'message': 'Modèles de détection d\'anomalies entraînés pour tous les appareils.'
                })
        except Exception as e:
            logger.error(f"Error during anomaly model training: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
                            
    # Chatbot route
    @app.route('/chatbot')
    @authentication_required
    def chatbot():
        device_id = session.get('device_id')
        
        # Get recent AI analyses
        analyses = AIAnalysis.query.filter_by(device_id=device_id).order_by(AIAnalysis.timestamp.desc()).limit(5).all()
        
        return render_template('chatbot.html', 
                            analyses=analyses,
                            device_id=device_id)
    
    # Chatbot API endpoint
    @app.route('/api/chat', methods=['POST'])
    @authentication_required
    def chat():
        device_id = session.get('device_id')
        data = request.json
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Invalid request'}), 400
        
        user_message = data['message']
        
        try:
            # Get the latest sensor data
            latest_data = SensorData.query.filter_by(device_id=device_id).order_by(SensorData.timestamp.desc()).first()
            
            # Get recent data points (last 24 hours)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
            recent_data = SensorData.query.filter_by(device_id=device_id).filter(
                SensorData.timestamp.between(start_date, end_date)
            ).order_by(SensorData.timestamp.asc()).all()
            
            # Get the latest weather data
            weather_data = WeatherData.query.filter_by(device_id=device_id).order_by(WeatherData.timestamp.desc()).first()
            
            # Create context for AI
            context = {
                'user_message': user_message,
                'device_id': device_id,
                'latest_data': latest_data,
                'recent_data': recent_data,
                'weather_data': weather_data,
                'language': session.get('language', 'fr')  # Get current language from session
            }
            
            # Generate AI response
            from ai import generate_chat_response
            response = generate_chat_response(context)
            
            return jsonify({'response': response}), 200
            
        except Exception as e:
            print(f"Error in chat API: {e}")
            return jsonify({'error': 'Failed to process your request', 'details': str(e)}), 500
    
    # API endpoint for generating analysis in current language
    @app.route('/api/generate-analysis-in-language', methods=['POST'])
    @authentication_required
    def generate_analysis_in_language():
        device_id = session.get('device_id')
        language = session.get('language', 'fr')
        
        try:
            # Generate AI analysis in the current language
            analysis = get_ai_analysis(device_id, language=language)
            
            if analysis:
                return jsonify({'success': True}), 200
            else:
                return jsonify({'success': False, 'error': 'Failed to generate analysis'}), 500
        except Exception as e:
            print(f"Error generating AI analysis: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # API endpoint for loading analyses history
    @app.route('/api/analyses')
    @authentication_required
    def get_analyses():
        device_id = session.get('device_id')
        
        # Get AI analyses
        analyses = AIAnalysis.query.filter_by(device_id=device_id).order_by(AIAnalysis.timestamp.desc()).limit(10).all()
        
        # Format analyses for JSON response
        analyses_data = []
        for analysis in analyses:
            analyses_data.append({
                'timestamp': analysis.timestamp.isoformat(),
                'analysis_text': analysis.analysis_text,
                'recommendations': analysis.recommendations
            })
        
        return jsonify({'analyses': analyses_data}), 200
        
    # API endpoint for device-specific data (for use in device_data.html)
    @app.route('/api/device/<device_id>/data')
    @authentication_required
    def get_device_data(device_id):
        # Check if requested device_id matches the logged-in device
        if session.get('device_id') != device_id:
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
        
        # Get optional limit parameter
        limit = request.args.get('limit', 100, type=int)
        
        # Get data from device-specific database
        from device_db_util import get_sensor_data_from_device_db
        data = get_sensor_data_from_device_db(device_id, limit=limit)
        
        return jsonify({'success': True, 'data': data}), 200
