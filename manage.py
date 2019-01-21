from flask import g

from app import create_app
from app import db

app = application = create_app()


def make_shell_context() -> dict:
    ctx = dict(app=app, g=g)

    for model_cls in db.Model.__subclasses__():
        ctx[model_cls.__name__] = model_cls

    return ctx


app.make_shell_context = make_shell_context
