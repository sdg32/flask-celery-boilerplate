__version__ = '1.0.1'

import importlib
import os
from typing import Any

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapper

from fcb.config import config_map
from fcb.ext.celery import FlaskCelery

db = SQLAlchemy()
tq = FlaskCelery()


def create_app(
        config_key: str | None = None,
        config_overrides: dict[str, Any] | None = None,
        instance_path: str | None = None,
) -> Flask:
    """Create Flask application.

    :param config_key: optional config environ key
    :param config_overrides: optional override default configurations
    :param instance_path: optional Flask instance path
    :return: Flask application
    """
    app = Flask('fcb', instance_relative_config=True,
                instance_path=instance_path)

    _load_configurations(app, config_key, config_overrides)
    _initialize_extensions(app)
    _make_shell_context(app)

    importlib.import_module('fcb.models')
    importlib.import_module('fcb.tasks')

    return app


def _load_configurations(
        app: Flask,
        key: str | None = None,
        overrides: dict[str, Any] | None = None,
) -> None:
    """Load application configurations."""
    key = key or os.getenv('FLASK_ENV') or 'development'
    cfg = config_map[key]()

    app.config.from_object(cfg)
    app.config.from_pyfile(cfg.EXTRA_INSTANCE_CONFIG, silent=True)
    app.config.from_envvar('FCB_SETTING', silent=True)
    app.config.from_mapping(overrides or {})

    cfg.init_app(app)


def _initialize_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    tq.init_app(app)


def _make_shell_context(app: Flask) -> None:
    """Make python shell context."""

    @app.shell_context_processor
    def _shell_context_processor() -> dict[str, Any]:
        mappers: frozenset[Mapper] = db.Model.registry.mappers
        models = {x.entity.__name__: x.entity for x in mappers}

        return dict(__version__=__version__, db=db, task_queue=tq, **models)
