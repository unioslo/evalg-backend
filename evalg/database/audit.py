"""
History and versioning support for SQLAlchemy using sqlalchemy-continuum.

This module implements custom configuration of sqlalchemy-continuum to support
tracking changes in evalg.

"""
import collections.abc
import logging
import reprlib

from sqlalchemy_continuum.plugins import TransactionMetaPlugin
from sqlalchemy_continuum.plugins.base import Plugin

logger = logging.getLogger(__name__)


class CallbackMapping(collections.abc.Mapping):
    """
    dict-like object with callbacks for getting updated values.

    This object can typically be used to provide updated data from e.g. a flask
    app or request context as default values for database fields.
    """

    def __init__(self):
        self._getters = dict()

    def __getitem__(self, item):
        return self._getters[item]

    def __iter__(self):
        return iter(self._getters)

    def __len__(self):
        return len(self._getters)

    @reprlib.recursive_repr()
    def __repr__(self):
        return '<{cls.__name__} at 0x{addr:02x}>'.format(
            cls=type(self),
            addr=id(self))

    def set_callback(self, key, getter):
        if not callable(getter):
            raise TypeError("invalid getter %r, must be a callable object" %
                            (getter,))
        self._getters[key] = getter

    def register(self, key):
        def wrapper(func):
            self.set_callback(key, func)
            return func
        return wrapper

    def get_value(self, column):
        return self[column]()

    def get_all(self):
        return {column: self.get_value(column) for column in self}


class AuditCallbacks(CallbackMapping):

    def __init__(self, *keys):
        self.keys = tuple(str(k) for k in keys)
        super(AuditCallbacks, self).__init__()

    def set_callback(self, key, getter):
        if self.keys and key not in self.keys:
            raise KeyError("invalid key %r, must be one of %r" %
                           (key, self.keys))
        super(AuditCallbacks, self).set_callback(key, getter)

    @reprlib.recursive_repr()
    def __repr__(self):
        keys = ', '.join(map(str, iter(self)))
        return '<{cls.__name__}{keys} at 0x{addr:02x}>'.format(
            cls=type(self),
            keys=(' ' + keys if keys else ''),
            addr=id(self))


class TransactionAuditPlugin(Plugin):
    """
    An implementation of FlaskPlugin that provides values from callbacks.
    """

    def __init__(self, source):
        self.source = source

    def transaction_args(self, uow, session):
        return self.source.get_all()


audit_plugin_source = AuditCallbacks('user_id', 'remote_addr')
audit_plugin = TransactionAuditPlugin(audit_plugin_source)


class TransactionArgsPlugin(TransactionMetaPlugin):
    """
    A subclass of TransactionMetaPlugin that adds keys/values from callbacks
    """

    def __init__(self, source):
        self.source = source

    def before_flush(self, uow, session):
        tx = uow.current_transaction
        for k, v in self.source.get_all().items():
            if k and v:
                tx.meta[k] = v


meta_plugin_source = CallbackMapping()
meta_plugin = TransactionArgsPlugin(meta_plugin_source)


# In evalg.wsgi.app:

@meta_plugin_source.register('foo')
def get_foo():
    return 'foo'


@audit_plugin_source.register('user_id')
def get_user_id():
    # TODO: Get Person object from request/request stack
    person = None
    if person:
        return person.id
    else:
        return None


@audit_plugin_source.register('remote_addr')
def get_remote_addr():
    # TODO: Get the real client ip from request/request stack
    return '127.0.0.1'
