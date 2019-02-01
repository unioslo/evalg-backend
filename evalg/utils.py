import datetime
import re

from flask import _request_ctx_stack
from collections.abc import Iterable

under_pat = re.compile(r'_([a-z])')


def underscore_to_camel(name):
    return under_pat.sub(lambda x: x.group(1).upper(), name)


def convert_json(data):
    return convert_json_internal(data, underscore_to_camel)


def convert_json_internal(data, convert):
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            new_data[convert(k)] = convert_json_internal(v, convert)
        return new_data
    elif isinstance(data, list):
        return [convert_json_internal(x, convert) for x in data]
    else:
        return data


def iterable_but_not_str(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, bytearray))


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


class ContextAttribute:
    """
    Use the request context to store object attribute values.
    """

    def __init__(self, name=None):
        self.name = str(name)

    def __repr__(self):
        return '{cls.__name__}(name={obj.name!r})'.format(cls=type(self),
                                                          obj=self)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        attr = self.mangled_attr(obj)
        return getattr(self.current_context, attr, None)

    def __set__(self, obj, value):
        attr = self.mangled_attr(obj)
        return setattr(self.current_context, attr, value)

    def __delete__(self, obj):
        attr = self.mangled_attr(obj)
        return delattr(self.current_context, attr)

    @property
    def current_context(self):
        return _request_ctx_stack.top

    def mangled_attr(self, owner):
        return '__{cls}_{sep}{addr}'.format(
            cls=type(self).__name__,
            sep='{}_'.format(self.name) if self.name else '',
            addr=id(owner))
