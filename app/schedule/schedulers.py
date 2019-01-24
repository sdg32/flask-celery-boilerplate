from celery import current_app as celery_app
from celery import schedules
from celery.beat import ScheduleEntry
from celery.beat import Scheduler
from celery.utils.encoding import safe_str
from celery.utils.encoding import safe_repr
from celery.utils.log import get_logger
from flask import current_app
import pytz

from app import db
from .models import CrontabSchedule
from .models import IntervalSchedule
from .models import SolarSchedule
from .models import PeriodicTask
from .models import PeriodicTasks

DEFAULT_MAX_INTERVAL = 5  # seconds

logger = get_logger(__name__)


def local_to_utc(dt):
    local = pytz.timezone(current_app.config['TIMEZONE'])
    local_dt = local.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc).replace(tzinfo=None)


class ModelEntry(ScheduleEntry):
    """Scheduler entry taken from database row."""

    model_schedules = (
        (schedules.crontab, CrontabSchedule, 'crontab'),
        (schedules.schedule, IntervalSchedule, 'interval'),
        (schedules.solar, SolarSchedule, 'solar'),
    )

    def __init__(self, model: PeriodicTask, app=None):
        """Initialize the model entry."""
        self.model = model
        app = app or celery_app._get_current_object()
        last_run_at = local_to_utc(model.last_run_at) if model.last_run_at else app.now()

        super().__init__(
            name=model.name,
            task=model.task_name,
            last_run_at=last_run_at,
            total_run_count=model.total_run_count,
            schedule=model.schedule,
            args=model.task_args,
            kwargs=model.task_kwargs,
            options={
                'queue': model.queue,
                'exchange': model.exchange,
                'routing_key': model.routing_key,
                'expires': model.expires,
                'priority': model.priority,
                'shadow': model.name,
            },
            app=app
        )

    def is_due(self):
        if not self.model.is_enabled:
            return schedules.schedstate(False, 5.0)

        if self.model.start_at and self.model.start_at > self.default_now():
            _, delay = self.schedule.is_due(self.last_run_at)
            return schedules.schedstate(False, delay)

        return self.schedule.is_due(self.last_run_at)

    def __next__(self):
        self.model.last_run_at = self.default_now()
        self.model.total_run_count += 1
        db.session.add(self.model)
        db.session.commit()
        return self.__class__(self.model)

    @classmethod
    def to_model_schedule(cls, schedule):
        for schedule_type, model_type, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                model_schedule = model_type.from_schedule(schedule)
                return model_schedule, model_field
        raise ValueError('Cannot convert schedule type %r to model.' % schedule)

    @classmethod
    def from_entry(cls, name, app=None, **entry):
        instance = PeriodicTask.query.filter_by(name=name).first()
        if not instance:
            instance = PeriodicTask(name=name)
        for k, v in cls._unpack_fields(**entry).items():
            setattr(instance, k, v)
        instance.desc = instance.name
        instance.is_preset = True
        db.session.add(instance)
        db.session.commit()

        return cls(instance, app=app)

    @classmethod
    def _unpack_fields(cls, schedule, task, args=None, kwargs=None, relative=None,
                       options=None, **entry):
        model_schedule, model_field = cls.to_model_schedule(schedule)
        entry.update(
            {
                model_field: model_schedule,
            },
            task_name=task,
            args=args or [],
            kwargs=kwargs or {},
            **cls._unpack_options(**options or {})
        )
        return entry

    @classmethod
    def _unpack_options(cls, queue=None, exchange=None, routing_key=None,
                        priority=None, **kwargs):
        return {
            'queue': queue,
            'exchange': exchange,
            'routing_key': routing_key,
            'priority': priority,
        }

    def __repr__(self):
        return '<ModelEntry: {0} {1}(*{2}, **{3}) {4}>'.format(
            safe_str(self.name), self.task, safe_repr(self.args),
            safe_repr(self.kwargs), self.schedule,
        )


class DatabaseScheduler(Scheduler):
    """Database-backed Beat Scheduler."""

    Entry = ModelEntry
    Model = PeriodicTask

    _schedule = None
    _last_timestamp = None
    _initial_read = True

    def __init__(self, *args, **kwargs):
        Scheduler.__init__(self, *args, **kwargs)
        self.max_interval = (
            kwargs.get('max_interval')
            or self.app.conf.beat_max_loop_interval
            or DEFAULT_MAX_INTERVAL
        )

    def setup_schedule(self):
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.beat_schedule)

    def all_as_schedule(self):
        logger.info('DatabaseScheduler: Fetching database schedule')
        s = {}
        for model in self.Model.query.filter_by(is_enabled=True).all():
            try:
                s[model.name] = self.Entry(model, app=self.app)
            except ValueError:
                pass
        return s

    def schedule_changed(self):
        last, ts = self._last_timestamp, PeriodicTasks.get_changed_at()
        try:
            if ts and ts > (last if last else ts):
                return True
        finally:
            self._last_timestamp = ts
        return False

    def update_from_dict(self, dict_):
        s = {}
        for name, entry_fields in dict_.items():
            try:
                entry = self.Entry.from_entry(name, app=self.app, **entry_fields)
                if entry.model.is_enabled:
                    s[name] = entry
            except Exception as err:
                logger.error('Cannot add entry %r to database schedule: %r. Contents: %r',
                             name, err, entry_fields)

        self.schedule.update(s)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.result_expires:
            entries.setdefault(
                'celery.backend_cleanup', {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*'),
                    'options': {'expires': 60 * 60 * 12}
                }
            )
        self.update_from_dict(entries)

    @property
    def schedule(self):
        update = False
        if self._initial_read:
            logger.info('DatabaseScheduler: Initial read')
            update = True
            self._initial_read = False

        elif self.schedule_changed():
            logger.info('DatabaseScheduler: Schedule changed')
            update = True

        if update:
            self._schedule = self.all_as_schedule()

        return self._schedule
