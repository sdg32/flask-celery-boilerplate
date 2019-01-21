from celery import current_app as celery_app
from celery import shared_task
from flask import current_app


@shared_task(name='print_app')
def print_app():
    print('Flask application: {}'.format(current_app))
    print('Celery application: {}'.format(celery_app))
