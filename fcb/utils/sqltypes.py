import json
from typing import Any
from uuid import UUID

from sqlalchemy.engine import Dialect
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
    cache_ok = True

    def process_bind_param(
            self,
            value: UUID | str | None,
            dialect: Dialect,
    ) -> str | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value.hex
        return UUID(value).hex

    def process_result_value(self, value: str, dialect: Dialect) -> UUID | None:
        if value is None:
            return value
        else:
            return UUID(value)


class JSON(TypeDecorator):
    """JSON column."""

    impl = TEXT
    cache_ok = True

    def process_bind_param(
            self,
            value: dict[Any, Any] | None,
            dialect: Dialect,
    ) -> str | None:
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(
            self,
            value: str | None,
            dialect: Dialect,
    ) -> dict[Any, Any] | None:
        if value is not None:
            return json.loads(value)
        return value


json_dict = MutableDict.as_mutable(JSON)
json_list = MutableList.as_mutable(JSON)
