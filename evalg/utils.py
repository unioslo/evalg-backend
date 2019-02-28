import datetime
import enum
import re

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
    return (
        isinstance(obj, Iterable) and
        not isinstance(obj, (str, bytes, bytearray)))


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


def make_descriptive_enum(name, values):
    """
    Make an enum of string constants with descriptions.

    >>> Values = make_descriptive_enum(
    ...     'Values',
    ...     {None: 'some values', 'foo': 'a foo value', 'bar': 'a bar value'})
    <enum 'Values'>
    >>> Values.foo
    <Values.foo: 'foo'>
    >>> Values('foo')
    <Values.foo: 'foo'>
    >>> Values.get_description()
    'some values'
    >>> Values.get_description('bar')
    'a bar value'
    >>> Values.foo.get_description()
    'a foo value'

    :type name: str
    :param name: Name of the enum

    :type values: dict
    :param values:
        A mapping of enum values and their description.
        The special key ``None`` will provide a description of the enum class.

    :rtype: enum.EnumMeta
    :return: An enum class with values and descriptions
    """

    def get_description(value=None):
        print('get_description(%r)' % (value, ))
        if isinstance(value, enum.Enum):
            value = value.value
        return values.get(value, '')

    _description_mixin = type(
        'DescriptiveEnum',
        (object, ),
        {'get_description': get_description})

    return enum.unique(
        enum.Enum(
            name,
            {v: v for v in values if v is not None},
            type=_description_mixin))
