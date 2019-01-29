import io
import reprlib

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta


class ReprBase(reprlib.Repr):
    """
    A reprlib.Repr class that allows setting limits from kwargs.
    """

    # defaults from reprlib.Repr.__init__()
    default_opts = {
        'maxlevel': 6,
        'maxtuple': 6,
        'maxlist': 6,
        'maxarray': 5,
        'maxdict': 4,
        'maxset': 6,
        'maxfrozenset': 6,
        'maxdeque': 6,
        'maxstring': 30,
        'maxlong': 40,
        'maxother': 30,
    }

    def __init__(self, *args, **kwargs):
        # in case reprlib.Repr ever gets some args, kwargs
        opts = dict((k, kwargs.pop(k, self.default_opts[k]))
                    for k in self.default_opts)
        super(ReprBase, self).__init__(*args, **kwargs)

        for k in opts:
            setattr(self, k, opts[k])


class PrimaryKeyRepr(ReprBase):
    """
    A repr-formatter for sqlalchemy models.
    """

    include_module = False

    def repr1(self, obj, level):
        if isinstance(type(obj), DeclarativeMeta):
            return self._repr_model(obj, level)
        else:
            return super(PrimaryKeyRepr, self).repr1(obj, level)

    def repr_UUID(self, obj, level):
        return self.repr1(str(obj), level - 1)

    def _repr_model(self, obj, level):
        return '<%s %s>' % (self._repr_class(obj, level),
                            self._repr_attrs(obj, level))

    def _repr_class(self, obj, level):
        if self.include_module:
            return '{cls.__module__}.{cls.__name__}'.format(cls=type(obj))
        else:
            return '{cls.__name__}'.format(cls=type(obj))

    def _repr_attr(self, obj, level):
        name, value = obj
        return '{}={}'.format(name, self.repr1(value, level - 1))

    def _repr_attrs(self, obj, level):
        attrs = (self._repr_attr((name, value), level)
                 for name, value in self._iter_attrs(obj))
        return ', '.join(attrs)

    def _iter_attrs(self, obj):
        attrs = (k.name for k in inspect(obj.__class__).primary_key)
        for name in attrs:
            yield (name, getattr(obj, name))


class PrettyFormatter(PrimaryKeyRepr):
    """
    A pretty formatter for sqlalchemy models.
    """

    indent = ' ' * 2

    def __init__(self, *args, **kwargs):
        self.indent = kwargs.pop('indent', self.indent)
        super(PrettyFormatter, self).__init__(*args, **kwargs)

    def repr1(self, obj, level):
        if isinstance(type(obj), DeclarativeMeta):
            return self._repr_model(obj, level)
        else:
            return super(PrimaryKeyRepr, self).repr1(obj, level)

    def repr_list(self, obj, level):
        return '\n\n'.join(self.repr1(o, level - 1) for o in obj)

    def repr_date(self, obj, level):
        return str(obj)

    def repr_datetime(self, obj, level):
        return str(obj)

    def repr_UUID(self, obj, level):
        return str(obj)

    def _repr_model(self, obj, level):
        output = io.StringIO()
        output.write(str(self._repr_class(obj, level)))
        is_first_attr = True
        for attr in self._iter_attrs(obj):
            if not is_first_attr:
                output.write(',')
            is_first_attr = False
            represented_attr = self._repr_attr(attr, level)
            output.write('\n' + self.indent + represented_attr)
        return output.getvalue()

    def _repr_attr(self, obj, level):
        name, value = obj
        return '{}: {}'.format(name, self.repr1(value, level - 1))

    def _iter_attrs(self, obj):
        attr_names = inspect(obj.__class__).columns.keys()
        for attr_name in attr_names:
            yield (attr_name, getattr(obj, attr_name))


def pretty_format(obj, maxstring=40, maxother=40, **kwargs):
    kwargs.update({
        'maxstring': maxstring,
        'maxother': maxother,
    })
    formatter = PrettyFormatter(**kwargs)
    return formatter.repr(obj)
