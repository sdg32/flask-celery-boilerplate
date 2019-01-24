# flask-celery-boilerplate

Celery Periodic Tasks backed by the Flask and SQLAlchemy

## Usage

Run celery beat:

```
celery beat -A celery_bin:app --loglevel info
```

Run celery workers:

```
celery worker -A celery_bin:app --loglevel info
```

Run celery workers (windows):

```
celery worker -A celery_bin:app --loglevel info --pool eventlet
```
