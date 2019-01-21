from app import create_app
from app import task_queue

flask = create_app()
app = celery = task_queue.celery
