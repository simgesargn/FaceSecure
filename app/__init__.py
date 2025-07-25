from flask import Flask
from config import Config
from loguru import logger
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Loglama yapılandırması
    logger.add(Config.LOG_FILE, rotation="10 MB", level="INFO")

    from app.routes import main_bp, auth_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    logger.info("Flask uygulaması başlatıldı.")
    return app