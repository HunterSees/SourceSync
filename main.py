import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.device import db
from src.routes.devices import devices_bp
from src.routes.sync import sync_bp
from src.routes.audio import audio_bp
from src.routes.system import system_bp

import warnings

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Secure SECRET_KEY
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev_syncstream_secret_key_2024_do_not_use_in_prod')
if SECRET_KEY == 'dev_syncstream_secret_key_2024_do_not_use_in_prod':
    warnings.warn("FLASK_SECRET_KEY is not set or uses the default development key. This is insecure for production.", UserWarning)
app.config['SECRET_KEY'] = SECRET_KEY

# Configure CORS
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS')
if CORS_ALLOWED_ORIGINS:
    origins = [origin.strip() for origin in CORS_ALLOWED_ORIGINS.split(',')]
else:
    warnings.warn("CORS_ALLOWED_ORIGINS is not set. Defaulting to restrictive CORS policy (currently none). For development, consider setting to 'http://localhost:3000' or similar.", UserWarning)
    origins = [] # Or a default like 'http://localhost:your_dev_port' if known
CORS(app, origins=origins, supports_credentials=True) # Added supports_credentials as it's often needed

# Register API blueprints
app.register_blueprint(devices_bp, url_prefix='/api')
app.register_blueprint(sync_bp, url_prefix='/api')
app.register_blueprint(audio_bp, url_prefix='/api')
app.register_blueprint(system_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    # For production environments, consider using a database migration tool
    # like Flask-Migrate (with Alembic) to manage schema changes.
    # db.create_all() is suitable for development and initial setup.
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

