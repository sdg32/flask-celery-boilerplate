from datetime import timedelta
from typing import Any

from flask import Flask


class BaseConfig:
    """Base configuration."""

    #: Flask secret key
    SECRET_KEY: str | bytes = 'f12cae1080574dd992ec22b378399616'
    #: Debug mode
    DEBUG: bool = False
    #: Testing mode
    TESTING: bool = False

    #: SQLAlchemy database URI
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'
    #: Whether to track modifications
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    #: Whether to record db queries
    SQLALCHEMY_RECORD_QUERIES: bool = True
    #: Slow query duration
    SQLALCHEMY_SLOW_QUERY: int | float = 0.5

    #: Celery broker URL
    CELERY_BROKER_URL: str = 'redis://localhost:6379/0'
    #: Celery enabled UTC time
    CELERY_ENABLE_UTC: bool = True
    #: Celery timezone
    CELERY_TIMEZONE: str = 'Asia/Shanghai'
    #: Celery BEAT schedules
    CELERY_BEAT_SCHEDULE: dict[str, Any] = {
        'print_app_every_10_seconds': {
            'task': 'print_app',
            'schedule': timedelta(seconds=10),
        }
    }
    #: Celery BEAT scheduler path
    CELERY_BEAT_SCHEDULER: str = 'fcb.schedulers:DatabaseScheduler'

    #: Extra config file in instance folder
    EXTRA_INSTANCE_CONFIG: str = 'config.py'

    def init_app(self, app: Flask) -> None:
        """Initialize app configuration.

        :param app: Flask application
        """
        pass


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True

    EXTRA_INSTANCE_CONFIG = 'config_dev.py'


class TestingConfig(BaseConfig):
    """Testing configuration."""

    TESTING = True

    EXTRA_INSTANCE_CONFIG = 'config_test.py'


class ProductionConfig(BaseConfig):
    """Production configuration."""

    EXTRA_INSTANCE_CONFIG = 'config.py'


config_map: dict[str, type[BaseConfig]] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
