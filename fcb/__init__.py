import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from . import tasks
from .schedule.extension import FlaskCelery

__version__ = '2020.1.0'

db = SQLAlchemy()
task_queue = FlaskCelery('FlaskCeleryBoilerplate')


def create_app(config_key: str = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    _load_config(app, config_key)

    db.init_app(app)
    task_queue.init_app(app)

    app.shell_context_processor(_make_shell_context)

    from .schedule import models

    return app


def _load_config(app: Flask, config_key: str):
    from fcb.config import config

    if not config_key:
        config_key = os.getenv('FLASK_ENV', 'default')

    app.config.from_object(config[config_key])
    app.config.from_pyfile('config.py', silent=True)
    config[config_key].init_app(app)


def _make_shell_context():
    ctx = dict(db=db, task_queue=task_queue)

    for model_cls in db.Model.__subclasses__():
        ctx[model_cls.__name__] = model_cls

    return ctx