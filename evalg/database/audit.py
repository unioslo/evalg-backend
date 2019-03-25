"""
History and versioning support for SQLAlchemy using sqlalchemy-continuum.

This module implements custom configuration of sqlalchemy-continuum to support
tracking changes in evalg.

"""

import collections.abc
import datetime
import reprlib
import sqlalchemy as sa

from collections import OrderedDict
from sqlalchemy_continuum.exc import ImproperlyConfigured
from sqlalchemy_continuum.plugins import TransactionMetaPlugin
from sqlalchemy_continuum.plugins.base import Plugin
from sqlalchemy_continuum.transaction import TransactionBase, TransactionFactory, create_triggers

from evalg.database.types import UtcDateTime, IpAddressType


def default_time(self):
    return datetime.datetime.now(datetime.timezone.utc)


class EvalgTransactionFactory(TransactionFactory):

    model_name = 'Transaction'

    def __init__(self, remote_addr=True):
        self.remote_addr = remote_addr

    def create_class(self, manager):
        """
        Create Transaction class.
        """

        class EvalgTransaction(
            manager.declarative_base,
            TransactionBase
        ):
            """
            Custom transaction class, used to override the default
            column types.

            Most of this class is copied from the Transaction class in Continuum

            Column changes:
            issued_at: Use our DateTime type with timezone, default value with timezone.
            remote_id: Use our own ip-address type.
            """

            __tablename__ = 'transaction'

            # Override issued_at from TransactionBase
            issued_at = sa.Column(
                UtcDateTime,
                default=default_time)

            id = sa.Column(
                sa.types.BigInteger,
                sa.schema.Sequence('transaction_id_seq'),
                primary_key=True,
                autoincrement=True
            )

            remote_addr = sa.Column(IpAddressType)

            user_cls = manager.user_cls
            registry = manager.declarative_base._decl_class_registry

            if isinstance(user_cls, str):
                try:
                    user_cls = registry[user_cls]
                except KeyError:
                    raise ImproperlyConfigured(
                        'Could not build relationship between Transaction'
                        ' and %s. %s was not found in declarative class '
                        'registry. Either configure VersioningManager to '
                        'use different user class or disable this '
                        'relationship ' % (user_cls, user_cls)
                    )

                user_id = sa.Column(
                    sa.inspect(user_cls).primary_key[0].type,
                    sa.ForeignKey(sa.inspect(user_cls).primary_key[0]),
                    index=True
                )
                user = sa.orm.relationship(user_cls)

            def __repr__(self):
                fields = ['id', 'issued_at', 'user']
                field_values = OrderedDict(
                    (field, getattr(self, field))
                    for field in fields
                    if hasattr(self, field)
                )
                return '<Transaction %s>' % ', '.join(
                    ('%s=%r' % (field, value)
                     for field, value in field_values.items())
                )

        if manager.options['native_versioning']:
            create_triggers(EvalgTransaction)
        return EvalgTransaction


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
