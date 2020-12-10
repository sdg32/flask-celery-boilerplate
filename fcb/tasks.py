from celery import current_app as celery_app
from celery import shared_task
from flask import current_app


@shared_task(name='print_app')
def print_app():
    print(f'flask: {current_app}, celery: {celery_app}')
