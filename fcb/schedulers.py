from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Sequence

import pytz
from celery import Celery
from celery import current_app as celery_app
from celery import schedules
from celery.beat import ScheduleEntry
from celery.beat import Scheduler
from celery.utils.log import get_logger
from flask import current_app
from kombu.utils.encoding import safe_repr
from kombu.utils.encoding import safe_str

from fcb.app import db
from fcb.models import CrontabSchedule
from fcb.models import IntervalSchedule
from fcb.models import ModelSchedule
from fcb.models import PeriodicTask
from fcb.models import PeriodicTasks
from fcb.models import SolarSchedule

TS = tuple[type[schedules.BaseSchedule], type[ModelSchedule], str]

DEFAULT_MAX_INTERVAL = 5  # seconds

logger = get_logger(__name__)


def local_to_utc(dt: datetime) -> datetime:
    """Convert local datetime to UTC datetime.

    :param dt: local datetime
    :return: UTC datetime
    """
    local = pytz.timezone(current_app.config['CELERY_TIMEZONE'])
    local_dt = local.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc).replace(tzinfo=None)


class ModelEntry(ScheduleEntry):
    """Scheduler entry taken from database row."""

    model_schedules: list[TS] = [
        (schedules.crontab, CrontabSchedule, 'crontab'),
        (schedules.schedule, IntervalSchedule, 'interval'),
        (schedules.solar, SolarSchedule, 'solar'),
    ]

    def __init__(self, model: PeriodicTask, app: Celery | None = None) -> None:
        """Initialize the model entry.

        :param model: model schedule
        :param app: optional Celery application
        """
        self.model = model
        app = app or celery_app._get_current_object()
        last_run_at = local_to_utc(model.last_run_at) if model.last_run_at \
            else app.now()

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

    @classmethod
    def from_entry(
            cls,
            name: str,
            app: Celery | None = None,
            **entry: Any,
    ) -> ModelEntry:
        """Get model entry from Celery task settings.

        :param name: task name
        :param app: optional Celery application
        :param entry: task settings
        :return: model entry
        """
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
    def to_model_schedule(
            cls,
            schedule: schedules.BaseSchedule,
    ) -> tuple[Any, str]:
        """Get model schedule from Celery schedule.

        :param schedule: celery schedule
        :return: model schedule & field name
        """
        for schedule_type, model_type, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                model_schedule = model_type.from_schedule(schedule)
                return model_schedule, model_field
        raise ValueError('Cannot convert schedule type %r to model.' % schedule)

    def is_due(self) -> schedules.schedstate:
        """Get schedule due state.

        :return: due state
        """
        if not self.model.is_enabled:
            return schedules.schedstate(False, 5.0)

        if self.model.start_at and self.model.start_at > self.default_now():
            _, delay = self.schedule.is_due(self.last_run_at)
            return schedules.schedstate(False, delay)

        return self.schedule.is_due(self.last_run_at)

    @classmethod
    def _unpack_fields(
            cls,
            schedule: schedules.BaseSchedule,
            task: str,
            args: Sequence[Any] | None = None,
            kwargs: dict[str, Any] | None = None,
            options: dict[str, Any] | None = None,
            **entry: Any,
    ) -> dict[str, Any]:
        """Unpack task setting fields."""
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
    def _unpack_options(
            cls,
            queue: str | None = None,
            exchange: str | None = None,
            routing_key: str | None = None,
            priority: int | None = None,
            **_: Any
    ) -> dict[str, Any]:
        """Unpack task setting options."""
        return {
            'queue': queue,
            'exchange': exchange,
            'routing_key': routing_key,
            'priority': priority,
        }

    def __next__(self) -> ModelEntry:
        self.model.last_run_at = self.default_now()
        self.model.total_run_count += 1
        db.session.add(self.model)
        db.session.commit()
        return self.__class__(self.model)

    def __repr__(self) -> str:
        return '<ModelEntry: {0} {1}(*{2}, **{3}) {4}>'.format(
            safe_str(self.name), self.task, safe_repr(self.args),
            safe_repr(self.kwargs), self.schedule,
        )


class DatabaseScheduler(Scheduler):
    """Database-backed Beat Scheduler."""

    Entry = ModelEntry
    Model = PeriodicTask

    _schedule: dict[str, ModelEntry] = {}
    _last_timestamp: datetime | None = None
    _initial_read: bool = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        Scheduler.__init__(self, *args, **kwargs)
        self.max_interval = (
                kwargs.get('max_interval')
                or self.app.conf.beat_max_loop_interval
                or DEFAULT_MAX_INTERVAL
        )

    @property
    def schedule(self) -> dict[str, ModelEntry]:
        """Model schedules."""
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

    def all_as_schedule(self) -> dict[str, ModelEntry]:
        """Retrieve all model schedules.

        :return: model schedules
        """
        logger.info('DatabaseScheduler: Fetching database schedule')
        s = {}
        for model in self.Model.query.filter_by(is_enabled=True).all():
            try:
                s[model.name] = self.Entry(model, app=self.app)
            except ValueError:
                pass
        return s

    def install_default_entries(self, data: dict[str, Any]) -> None:
        """Install default BEAT schedules.

        :param data: task settings
        """
        entries: dict[str, Any] = {}
        if self.app.conf.result_expires:
            entries.setdefault(
                'celery.backend_cleanup', {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*'),
                    'options': {'expires': 60 * 60 * 12}
                }
            )
        self.update_from_dict(entries)

    def schedule_changed(self) -> bool:
        """Is task changed.

        :return: boolean
        """
        last, ts = self._last_timestamp, PeriodicTasks.get_changed_at()
        try:
            if ts and ts > (last if last else ts):
                return True
        finally:
            self._last_timestamp = ts
        return False

    def setup_schedule(self) -> None:
        """Setup BEAT schedule."""
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.beat_schedule)

    def update_from_dict(self, dict_: dict[str, Any]) -> None:
        """Update BEAT schedule from task settings.

        :param dict_: task settings
        """
        s = {}
        for name, entry_fields in dict_.items():
            try:
                entry = self.Entry.from_entry(name, app=self.app,
                                              **entry_fields)
                if entry.model.is_enabled:
                    s[name] = entry
            except Exception as err:
                logger.error(
                    f'Cannot add entry {name} to database schedule: {err!r}. '
                    f'Contents: {entry_fields!r}',
                )

        self.schedule.update(s)
