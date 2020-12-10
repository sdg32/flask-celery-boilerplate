import json
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import CHAR
from sqlalchemy.types import TEXT
from sqlalchemy.types import TypeDecorator

__all__ = [
    'GUID', 'json_dict', 'json_list',
]


class GUID(TypeDecorator):
    """GUID column."""

    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        elif dialect.name == 'postgresql':
            return str(value)

        if not isinstance(value, uuid.UUID):
            try:
                return '%.32x' % int(uuid.UUID(value))
            except ValueError:
                return None
        else:
            return '%.32x' % int(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)

    @staticmethod
    def gen_value():
        return uuid.uuid4()


class JSON(TypeDecorator):
    """JSON column."""

    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                value = json.loads(value)
            except ValueError:
                value = None
        return value


json_dict = MutableDict.as_mutable(JSON)
json_list = MutableList.as_mutable(JSON)
