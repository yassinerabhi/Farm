import os
import logging
from datetime import datetime
import re

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import translation module
from translations import init_translations, _

# Custom Jinja2 filters
def nl2br(value):
    """Convert newlines to <br> tags."""
    if not value:
        return ""
    # First convert newlines to <br>
    value = re.sub(r'\r\n|\r|\n', '<br>\n', value)
    # Then wrap in Markup to prevent escaping
    return Markup(value)

class Base(DeclarativeBase):
    pass

# Initialize database
db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///agro_iot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Register custom Jinja2 filters
app.jinja_env.filters['nl2br'] = nl2br

# Initialize translations
init_translations(app)

# Import routes and API after initializing db to avoid circular imports
from routes import register_routes
from api import api_bp

# Register routes and blueprints
with app.app_context():
    # Import models for table creation
    import models
    
    # Create database tables
    db.create_all()
    
    # Register routes
    register_routes(app)
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
