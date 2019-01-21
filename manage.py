from flask import g

from app import create_app
from app import db
from app import task_queue

app = application = create_app()


def make_shell_context() -> dict:
    ctx = dict(app=app, g=g, db=db, task_queue=task_queue)

    for model_cls in db.Model.__subclasses__():
        ctx[model_cls.__name__] = model_cls

    return ctx


app.make_shell_context = make_shell_context
