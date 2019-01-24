from app import create_app
from app import task_queue

flask = create_app()
flask_context = flask.app_context()
flask_context.push()

app = celery = task_queue.celery
