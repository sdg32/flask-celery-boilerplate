from fcb import create_app
from fcb import task_queue

flask = create_app()
flask_context = flask.app_context()
flask_context.push()

app = celery = task_queue.celery
