import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_key: str = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    _load_config(app, config_key)

    db.init_app(app)

    return app


def _load_config(app: Flask, config_key: str):
    from config import config

    if not config_key:
        config_key = os.getenv('FLASK_ENV', 'default')

    app.config.from_object(config[config_key])
    app.config.from_pyfile('config.py', silent=True)
    config[config_key].init_app(app)
