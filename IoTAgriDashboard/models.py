from datetime import datetime
from app import db

class Device(db.Model):
    id = db.Column(db.String(12), primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sensor_data = db.relationship('SensorData', backref='device', lazy=True)
    alerts = db.relationship('Alert', backref='device', lazy=True)
    
    def __repr__(self):
        return f'<Device {self.id}>'

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(12), db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Basic sensor data
    moisture = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=True)
    ec = db.Column(db.Integer, nullable=True)  # Electrical conductivity
    ph = db.Column(db.Float, nullable=True)
    
    # Nutrient data
    nitrogen = db.Column(db.Integer, nullable=True)
    phosphorous = db.Column(db.Integer, nullable=True)
    potassium = db.Column(db.Integer, nullable=True)
    salinity = db.Column(db.Float, nullable=True)
    
    # Environmental data
    bme_temperature = db.Column(db.Float, nullable=True)
    bme_humidity = db.Column(db.Float, nullable=True)
    bme_pressure = db.Column(db.Float, nullable=True)
    bme_gas = db.Column(db.Float, nullable=True)
    uv_index = db.Column(db.Float, nullable=True)
    rain_level = db.Column(db.Integer, nullable=True)  # 0-100 percentage
    
    # Battery info
    battery_voltage = db.Column(db.Float, nullable=True)
    battery_percentage = db.Column(db.Integer, nullable=True)
    
    # Wake-up reason
    wakeup_reason = db.Column(db.String(20), nullable=True)
    
    def __repr__(self):
        return f'<SensorData {self.id}>'

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(12), db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(50), nullable=False)  # moisture, temperature, battery, etc.
    message = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # info, warning, danger
    acknowledged = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Alert {self.id}: {self.type}>'

class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(12), db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Current weather
    temperature = db.Column(db.Float, nullable=True)
    feels_like = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Integer, nullable=True)
    pressure = db.Column(db.Integer, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    wind_direction = db.Column(db.Integer, nullable=True)
    weather_main = db.Column(db.String(50), nullable=True)
    weather_description = db.Column(db.String(100), nullable=True)
    clouds = db.Column(db.Integer, nullable=True)
    rain_1h = db.Column(db.Float, nullable=True)
    rain_3h = db.Column(db.Float, nullable=True)
    
    # Forecast data can be stored in a separate table if needed
    
    def __repr__(self):
        return f'<WeatherData {self.id}>'

class AIAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(12), db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_text = db.Column(db.Text, nullable=False)
    recommendations = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<AIAnalysis {self.id}>'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(12), db.ForeignKey('device.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<Report {self.id}: {self.title}>'
