import os

root_dir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'some secret string')
    DEBUG = False
    TESTING = False
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')

    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_SLOW_QUERY = 0.5

    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_ENABLE_UTC = True
    CELERY_TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')
    CELERY_BEAT_SCHEDULE = {}
    CELERY_BEAT_SCHEDULER = 'fcb.schedule.schedulers:DatabaseScheduler'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DEV_DATABASE_URI',
        'sqlite:///{}'.format(os.path.join(root_dir, 'db_dev.sqlite3'))
    )


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URI',
        'sqlite:///:memory:'
    )


class ProductionConfig(BaseConfig):

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI',
        'sqlite:///{}'.format(os.path.join(root_dir, 'db.sqlite3'))
    )


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig,
}
