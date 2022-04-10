import importlib
import os
from typing import FrozenSet

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapper

from fcb.ext.celery import FlaskCelery
from .config import config

db = SQLAlchemy()
tq = FlaskCelery()


def create_app(config_key: str = None, config_override: dict = None) -> Flask:
    """Create flask application."""
    app = Flask('fcb', instance_relative_config=True)

    # Load config
    cfg = config[config_key or os.getenv('FLASK_ENV', 'default')]()
    cfg.init_app(app, config_override)

    # Initial extensions
    db.init_app(app)
    tq.init_app(app)

    # Add python shell context
    app.shell_context_processor(_make_shell_context)

    importlib.import_module('fcb.models')
    importlib.import_module('fcb.tasks')

    return app


def _make_shell_context() -> dict:
    """Make python shell context."""
    from . import __version__

    mappers: FrozenSet[Mapper] = db.Model.registry.mappers
    models = {x.entity.__name__: x.entity for x in mappers}

    return dict(__version__=__version__,
                db=db, task_queue=tq,
                **models)
