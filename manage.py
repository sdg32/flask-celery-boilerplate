from fcb.app import create_app
from fcb.app import tq

flask = create_app()
flask_context = flask.app_context()
flask_context.push()

app = celery = tq.celery
