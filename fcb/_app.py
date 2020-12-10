import importlib
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from fcb.ext.celery import FlaskCelery
from .config import config

db = SQLAlchemy()
tq = FlaskCelery('fcb')


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

    model_registry = getattr(db.Model, '_decl_class_registry')
    models = {k: v for k, v in model_registry.items()
              if k != '_sa_module_registry'}

    return dict(__version__=__version__,
                db=db, task_queue=tq,
                **models)
