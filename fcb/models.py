from datetime import datetime
from datetime import timedelta

from celery import schedules
from sqlalchemy import inspect

from fcb import db
from fcb.utils.sqltypes import GUID
from fcb.utils.sqltypes import json_dict
from fcb.utils.sqltypes import json_list


class CrontabSchedule(db.Model):
    """Crontab-like schedule."""

    __tablename__ = 'crontab_schedule'

    id = db.Column(GUID, default=GUID.gen_value, primary_key=True)
    minute = db.Column(db.String(50), default='*')
    hour = db.Column(db.String(50), default='*')
    day_of_week = db.Column(db.String(50), default='*')
    day_of_month = db.Column(db.String(50), default='*')
    month_of_year = db.Column(db.String(50), default='*')

    @classmethod
    def from_schedule(cls, schedule: schedules.crontab) -> 'CrontabSchedule':
        spec = {
            'minute': schedule._orig_minute,
            'hour': schedule._orig_hour,
            'day_of_week': schedule._orig_day_of_week,
            'day_of_month': schedule._orig_day_of_month,
            'month_of_year': schedule._orig_month_of_year
        }
        instance = cls.query.filter_by(**spec).first()
        if not instance:
            instance = cls(**spec)
        db.session.add(instance)
        db.session.commit()
        return instance

    @property
    def schedule(self) -> schedules.crontab:
        return schedules.crontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year,
        )

    def __repr__(self):
        return '<CrontabSchedule ' \
               '{0.minute} {0.hour} {0.day_of_week} {0.day_of_month} {0.month_of_year} ' \
               '(m/h/d/dM/MY)>'.format(self)

    def __str__(self):
        return '{0.minute} {0.hour} {0.day_of_week} {0.day_of_month} {0.month_of_year} ' \
               '(m/h/d/dM/MY)'.format(self)


class IntervalSchedule(db.Model):
    """Schedule executing every n seconds."""

    __tablename__ = 'interval_schedule'

    id = db.Column(GUID, default=GUID.gen_value, primary_key=True)
    every = db.Column(db.Integer)
    period = db.Column(db.String(20))
    seconds = db.Column(db.Integer)

    @classmethod
    def from_schedule(cls, schedule: schedules.schedule, period: str = 'seconds') -> 'IntervalSchedule':
        seconds = max(schedule.run_every.total_seconds(), 0)
        instance = cls.query.filter_by(seconds=seconds).first()
        if not instance:
            instance = cls(every=seconds, period=period)
        db.session.add(instance)
        db.session.commit()
        return instance

    @property
    def schedule(self) -> schedules.schedule:
        return schedules.schedule(timedelta(**{self.period: self.every}))

    def __repr__(self):
        return '<IntervalSchedule {0.every} {0.period}>'.format(self)

    def __str__(self):
        return 'Every {0.every} {0.period}'.format(self)


class SolarSchedule(db.Model):
    """Schedule following astronomical patterns."""

    __tablename__ = 'solar_schedule'

    id = db.Column(GUID, default=GUID.gen_value, primary_key=True)
    event = db.Column(db.String(20))
    latitude = db.Column(db.Numeric(9, 6))
    longitude = db.Column(db.Numeric(9, 6))

    @classmethod
    def from_schedule(cls, schedule: schedules.solar) -> 'SolarSchedule':
        spec = {
            'event': schedule.event,
            'latitude': schedule.lat,
            'longitude': schedule.lon,
        }
        instance = cls.query.filter_by(**spec).first()
        if not instance:
            instance = cls(**spec)
        db.session.add(instance)
        db.session.commit()
        return instance

    @property
    def schedule(self) -> schedules.solar:
        return schedules.solar(self.event, self.latitude, self.longitude)

    def __repr__(self):
        return '<SolarSchedule {0.event} {0.latitude} {0.longitude}>'.format(self)

    def __str__(self):
        latitude = 'N{}'.format(self.latitude) \
            if self.latitude > 0 else 'S{}'.format(-self.latitude)
        longitude = 'E{}'.format(self.longitude) \
            if self.longitude > 0 else 'W{}'.format(-self.longitude)
        return '{event} ({latitude} {longitude})'.format(
            event=self.event,
            latitude=latitude, longitude=longitude,
        )


class PeriodicTask(db.Model):
    """Model representing a periodic task."""

    __tablename__ = 'periodic_task'

    id = db.Column(GUID, default=GUID.gen_value, primary_key=True)
    name = db.Column(db.String(200), unique=True, index=True)
    desc = db.Column(db.String(200))
    is_preset = db.Column(db.Boolean, default=False)
    is_enabled = db.Column(db.Boolean, default=True)
    last_run_at = db.Column(db.DateTime)
    total_run_count = db.Column(db.Integer, default=0)
    remarks = db.Column(db.Text)

    task_name = db.Column(db.String(200))
    task_args = db.Column(json_list, default=[])
    task_kwargs = db.Column(json_dict, default={})
    queue = db.Column(db.String(200))
    exchange = db.Column(db.String(200))
    routing_key = db.Column(db.String(200))
    expires = db.Column(db.Integer)
    start_at = db.Column(db.DateTime)
    priority = db.Column(db.Integer)

    crontab_id = db.Column(GUID, db.ForeignKey('crontab_schedule.id'), index=True)
    crontab = db.relationship('CrontabSchedule')  # type: CrontabSchedule
    interval_id = db.Column(GUID, db.ForeignKey('interval_schedule.id'), index=True)
    interval = db.relationship('IntervalSchedule')  # type: IntervalSchedule
    solar_id = db.Column(GUID, db.ForeignKey('solar_schedule.id'), index=True)
    solar = db.relationship('SolarSchedule')  # type: SolarSchedule

    @property
    def schedule(self):
        if self.interval:
            return self.interval.schedule
        elif self.crontab:
            return self.crontab.schedule
        elif self.solar:
            return self.solar.schedule


class PeriodicTasks(db.Model):
    __tablename__ = 'periodic_tasks'

    id = db.Column(db.Integer, primary_key=True)
    changed_at = db.Column('changed_at', db.DateTime, default=datetime.now)

    @classmethod
    def get_changed_at(cls) -> datetime:
        instance = cls.query.get(1)
        if not instance:
            instance = cls(id=1)
            db.session.add(instance)
            db.session.commit()

        return instance.changed_at


@db.event.listens_for(IntervalSchedule, 'before_insert')
@db.event.listens_for(IntervalSchedule, 'before_update')
def _automatic_update_interval_seconds(mapper, connection, target):
    target.seconds = timedelta(**{target.period: target.every}).total_seconds()


@db.event.listens_for(CrontabSchedule, 'after_insert')
@db.event.listens_for(CrontabSchedule, 'after_update')
@db.event.listens_for(CrontabSchedule, 'after_delete')
@db.event.listens_for(IntervalSchedule, 'after_insert')
@db.event.listens_for(IntervalSchedule, 'after_update')
@db.event.listens_for(IntervalSchedule, 'after_delete')
@db.event.listens_for(SolarSchedule, 'after_insert')
@db.event.listens_for(SolarSchedule, 'after_update')
@db.event.listens_for(SolarSchedule, 'after_delete')
@db.event.listens_for(PeriodicTask, 'after_insert')
@db.event.listens_for(PeriodicTask, 'after_delete')
def _automatic_refresh(mapper, connection, target):
    _update_changed_time(connection)


@db.event.listens_for(PeriodicTask, 'after_update')
def _automatic_refresh2(mapper, connection, target):
    def is_changed():
        for name, attr in inspect(target).attrs.items():
            history = attr.history
            if name not in ['last_run_at', 'total_run_count'] and history.deleted:
                return True
        return False

    if is_changed():
        _update_changed_time(connection)


def _update_changed_time(cnn):
    t = PeriodicTasks.__table__

    rv = cnn.execute(t.select(t.c.id == 1)).fetchone()
    if not rv:
        cnn.execute(t.insert().values(id=1, changed_at=datetime.now()))
    else:
        cnn.execute(t.update().where(t.c.id == 1).values(changed_at=datetime.now()))
