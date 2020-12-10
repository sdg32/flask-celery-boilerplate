from fcb import create_app
from fcb import tq

flask = create_app()
flask_context = flask.app_context()
flask_context.push()

app = celery = tq.c
