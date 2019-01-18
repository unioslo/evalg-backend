import datetime
import re

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


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
