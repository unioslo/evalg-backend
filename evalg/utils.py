import datetime
import enum
import re


from collections.abc import Iterable, Mapping
from flask import g
from functools import wraps
from types import DynamicClassAttribute

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
    return (
        isinstance(obj, Iterable) and
        not isinstance(obj, (str, bytes, bytearray)))


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


class _DescriptiveEnumMixin(object):

    def get_description(self):
        return ''

    @DynamicClassAttribute
    def description(self):
        return self.get_description()


def make_descriptive_enum(name, values, description=None):
    """
    Make an enum of string constants with descriptions.

    >>> Values = make_descriptive_enum(
    ...     'Values',
    ...     {'foo': 'a foo value', 'bar': 'a bar value'},
    ...     description='some_values')
    >>> Values
    <enum 'Values'>
    >>> Values.foo
    <Values.foo: 'foo'>
    >>> Values('foo')
    <Values.foo: 'foo'>
    >>> Values.get_description()
    'some values'
    >>> Values.get_description('bar')
    'a bar value'
    >>> Values.foo.description
    'a foo value'

    :type name: str
    :param name: Name of the enum

    :type values: dict
    :param values: A mapping of enum values and their description.

    :type description: str
    param description: A description of the enum class:

    :rtype: enum.EnumMeta
    :return: An enum class with values and descriptions
    """

    class_description = description
    enum_values = {v: v for v in values}
    enum_descriptions = {v: values[v] for v in values}

    def get_description(value=None):
        if not value:
            return class_description or ''
        if isinstance(value, enum.Enum):
            value = value.value
        return enum_descriptions.get(value, '')

    description_mixin = type(
        '_{name}_DescriptiveEnum'.format(name=name),
        (_DescriptiveEnumMixin, ),
        {'get_description': get_description})

    return enum.unique(
        enum.Enum(name, enum_values, type=description_mixin))


class Name2Callable(Mapping):
    def __init__(self):
        self.map = {}
        self.last_item_added = None

    def __iter__(self):
        iter(self.map)

    def __len__(self):
        len(self.map)

    def __getitem__(self, item):
        return self.map[item]

    def __call__(self, callable_, **kwargs):
        self.map[callable_.__name__] = callable_
        self.last_item_added = callable_
        return callable_


def flask_request_memoize(f):
    """
    Flask memoize wrapper for a callable.

    Based on the same wrapper i Cerebrum.utils.funcwrap.
    Caching is done via flask.g and will be removed when the session ends.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        arg_string = f'{args}{kwargs}'
        if arg_string not in g:
            setattr(g, arg_string, f(*args, **kwargs))
        return getattr(g, arg_string)
    return wrapper
