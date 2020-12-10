from celery import Celery
from celery.app.task import Task as BaseTask
from flask import Flask
from flask import has_app_context


class FlaskCelery:
    """Flask celery extension."""

    _celery: Celery = None
    app: Flask = None

    def __init__(self, name: str, app: Flask = None):
        self._celery = Celery(name)
        self.app = app

        if app is not None:
            self.init_app(app)

    @property
    def c(self) -> Celery:
        return self._celery

    @property
    def task(self):
        return self._celery.task

    def init_app(self, app: Flask):
        self._celery.conf.update(app.config.get_namespace('CELERY_'))

        class ContextTask(BaseTask):

            def run(self, *args, **kwargs):
                raise NotImplementedError()

            def __call__(self, *args, **kwargs):
                if has_app_context():
                    return super().__call__(*args, **kwargs)
                with app.app_context():
                    return super().__call__(*args, **kwargs)

        self._celery.task_cls = ContextTask
        app.extensions['celery'] = self
