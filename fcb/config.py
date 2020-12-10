import os
from datetime import timedelta

from dotenv import dotenv_values
from flask import Flask


class BaseConfig:
    # region Flask config
    SECRET_KEY = b'\x1c\xea\xabzG\x887\x1b\x0fM\x10#cwM=O\xb7\xe7>>\xed\xef)'
    DEBUG = False
    TESTING = False
    # endregion

    # region ORM config
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_SLOW_QUERY = 0.5
    # endregion

    # region Celery config
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_ENABLE_UTC = True
    CELERY_TIMEZONE = 'Asia/Shanghai'
    CELERY_BEAT_SCHEDULE = {
        'print_app_every_10_seconds': {
            'task': 'print_app',
            'schedule': timedelta(seconds=10),
        }
    }
    CELERY_BEAT_SCHEDULER = 'fcb.schedulers:DatabaseScheduler'
    # endregion

    # Additional flask config file
    additional: str = 'config.py'

    def init_app(self, app: Flask, override: dict = None):
        mapping = {k: v for k, v in dotenv_values().items()
                   if not k.startswith('FLASK_')}
        mapping |= (override or {})

        app.config.from_object(self)
        app.config.from_pyfile(self.additional, silent=True)
        app.config.from_mapping(mapping)

        # Default database uri
        if not app.config['SQLALCHEMY_DATABASE_URI']:
            db_file = os.path.join(app.instance_path, 'sqlite3.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'


class DevelopmentConfig(BaseConfig):
    DEBUG = True

    additional = 'config_dev.py'


class TestingConfig(BaseConfig):
    TESTING = True

    additional = 'config_test.py'


class ProductionConfig(BaseConfig):
    additional = 'config.py'


config: dict[str, type[BaseConfig]] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig,
}
