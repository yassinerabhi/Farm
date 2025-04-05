import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///agro_iot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OpenWeatherMap API key
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', 'a2fb057ca6d0c40d05376d4ee8bad6ac')
    
    # Google Gemini API key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBrKN0yZ8y9rQH9EgJoZpHvi3_re4V_2dk')
    
    # Alert thresholds
    MOISTURE_MIN = 20
    MOISTURE_MAX = 80
    TEMPERATURE_MIN = 10
    TEMPERATURE_MAX = 35
    PH_MIN = 5.5
    PH_MAX = 8.0
    EC_MIN = 500
    EC_MAX = 3000
    BATTERY_MIN = 20

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
# Select configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])
