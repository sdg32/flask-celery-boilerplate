from typing import Any

from celery import Celery
from celery.app.task import Task as BaseTask
from flask import Flask
from flask import current_app
from flask import has_app_context


class FlaskCelery:
    """Flask celery extension.

    :param app: optional Flask application
    """

    app: Flask | None = None

    def __init__(self, app: Flask | None = None) -> None:
        self.app = app

        if app is not None:
            self.init_app(app)

    @property
    def celery(self) -> Celery:
        """Celery application."""
        state: _CeleryState = current_app.extensions['celery']
        return state.celery

    def init_app(self, app: Flask) -> None:
        """Initialize extension.

        :param app: Flask application
        """

        class ContextTask(BaseTask):
            """Celery task within Flask context."""

            def run(self, *args: Any, **kwargs: Any) -> Any:
                raise NotImplementedError()

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                if has_app_context():
                    return super().__call__(*args, **kwargs)
                with app.app_context():
                    return super().__call__(*args, **kwargs)

        client = Celery(app.import_name, task_cls=ContextTask)
        client.conf.update(app.config.get_namespace('CELERY_'))

        app.extensions['celery'] = _CeleryState(client)


class _CeleryState:
    """Flask celery extension state.

    :param celery: Celery application
    """

    celery: Celery

    def __init__(self, celery: Celery) -> None:
        self.celery = celery
