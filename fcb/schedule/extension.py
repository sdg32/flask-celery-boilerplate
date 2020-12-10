from celery import Celery
from celery.app.task import Task as BaseTask
from flask import Flask


class FlaskCelery:
    """Flask celery extension."""

    celery = None  # type: Celery
    flask = None  # type: Flask

    def __init__(self, name: str, app: Flask = None):
        self.celery = Celery(name)
        self.flask = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self._load_config(app)

        class ContextTask(BaseTask):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return super().__call__(*args, **kwargs)

        self.celery.task_cls = ContextTask
        app.extensions['celery'] = self

    @property
    def task(self):
        return self.celery.task

    def _load_config(self, app: Flask):
        """Load config from flask."""
        for k, v in app.config.items():
            if not k.startswith('CELERY_'):
                continue
            self.celery.conf[k[7:].lower()] = v
