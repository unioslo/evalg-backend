"""
Database models for votes.

Leaving a vote
--------------
To leave a new vote, you'll have to:

1. Create and save a ballot - this gives you a unique ``ballot_id``.
2. Create and save a new py:class:`Vote` that references the ``ballot_id``.

When a new py:class:`Vote` is stored, a py:class:`VoteRecord` is automatically
populated and stored alongside it.

Updating vote
-------------
To change a vote if already given:

1. Create and save a ballot - this gives you a unique ``ballot_id``.
2. Find previous vote (based on ``voter_id``), and update its ``ballot_id``

When a new py:class:`Vote` is modified, a new py:class:`VoteRecord` is
automatically populated and stored alongside it.

Deleting a vote
---------------
To delete a vote, simply find it and delete. Note that any
py:class:`VoteRecord`s will be left behind.

Adding data to vote records
---------------------------
Specific fields of the VoteRecord model can be auto-populated from functions.
These fields are:

- ip_addr
- user

::

    import flask
    from evalg.models import votes

    @votes.vote_record_data.register('ip_addr')
    def get_ip_addr():
        try:
            return flask.request.remote_addr
        except Exception:
            logger.error('unable to get client ip', exc_info=True)
            return None


    @votes.vote_record_data.register('user')
    def get_user():
        return None

"""
import collections.abc
import logging
import reprlib

import sqlalchemy.event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import exists, and_, schema, sqltypes
from sqlalchemy.orm import relationship
from sqlalchemy.orm.base import NEVER_SET, NO_VALUE

import evalg.database.types
from evalg.utils import utcnow
from .base import ModelBase
from .voter import Voter


logger = logging.getLogger(__name__)


# TODO: There are probably better ways of implementing this.
# TODO: Consider using SQLAlchemy-Continuum
# NOTE: If we need this pattern to auto-populate fields elsewhere, this should
# be moved to a sub-module of evalg.database, or perhaps into evalg.models.base


class Datasource(collections.abc.Mapping):
    """
    dict-like object with callbacks for getting updated values.

    This object can typically be used to provide updated data from e.g. a flask
    app or request context as default values for database fields.

    e.g.:

        request_data = Datasource('client_ip', 'user_id')

        @request_data.register('client_ip')
        def get_ip():
            return flask.request.remote_addr

        sqlalchemy.event.listen(SomeObject, 'before_insert',
                                request_data.before_insert_handler)
    """

    def __init__(self, *keys):
        self.keys = tuple(str(k) for k in keys)
        self._getters = dict()

    def __getitem__(self, item):
        return self._getters[item]

    def __iter__(self):
        return iter(self._getters)

    def __len__(self):
        return len(self._getters)

    @reprlib.recursive_repr()
    def __repr__(self):
        keys = ', '.join(map(str, iter(self)))
        return '<{cls.__name__}{keys} at 0x{addr:02x}>'.format(
            cls=type(self),
            keys=(' ' + keys if keys else ''),
            addr=id(self))

    def set_callback(self, key, getter):
        if self.keys and key not in self.keys:
            raise KeyError("invalid key %r, must be one of %r" %
                           (key, self.keys))
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

    def before_insert_handler(self, mapper, connection, target):
        """
        update columns from on ``"before_insert"`` from this object.
        """
        for column in self:
            setattr(target, column, self.get_value(column))


class Vote(ModelBase):
    """
    The Vote object represents the *current* ballot for a given voter.
    """

    __tablename__ = 'vote'

    # TODO: Find out what other constraints we'd need? One vote per election?

    voter_id = schema.Column(
        schema.ForeignKey('voter.id'),
        primary_key=True,
    )

    ballot_id = schema.Column(
        schema.ForeignKey('vote_log.ballot_id'),
        index=True,
        nullable=False,
    )

    voter = relationship(
        "Voter",
        back_populates="votes",
    )

    record = relationship(
        "VoteRecord",
        back_populates="vote",
    )

    @hybrid_property
    def is_approved(self):
        """ whether this vote comes from an approved voter or not. """
        return self.voter.voter_status.code != "unapproved"

    @is_approved.expression
    def is_approved(self):
        return exists([Vote]).where(
            and_(
                self.voter_id == Voter.id,
                Voter.voter_status_id != "unapproved"))


class VoteRecord(ModelBase):
    """
    The VoteRecord represents *all* votes left by a given voter.
    """

    __tablename__ = 'vote_log'

    # ballot_id is a reference to a ballot.
    # the ballot *may* not reside in this database -- how would be set up this?
    ballot_id = schema.Column(
        evalg.database.types.UuidType,
        doc='reference to the ballot',
        primary_key=True,
    )

    voter_id = schema.Column(
        schema.ForeignKey('voter.id'),
        doc='reference to the voter who cast the ballot',
        index=True,
        nullable=False,
    )

    logged_at = schema.Column(
        evalg.database.types.UtcDateTime,
        default=utcnow,
        doc='timestamp of the change',
        index=True,
        nullable=False,
    )

    ip_addr = schema.Column(
        evalg.database.types.IpAddressType,
        doc='client ip that stored this vote',
        nullable=True,
    )

    user = schema.Column(
        sqltypes.UnicodeText,
        doc='authenticated user that stored this vote',
        nullable=True,
    )

    vote = relationship(
        'Vote',
        doc='link to the vote if this record is a current vote',
        back_populates="record",
    )


def vote_record_copy(target_column):
    """
    Generate a function that copies columns to a VoteRecord

    The function generated by ``vote_record_copy('ballot_id')`` would typically
    be bound to a ``Vote.ballot_id "set"`` event. Whenever a
    ``Vote.ballot_id`` is set, this function would ensure that a ``VoteRecord``
    exists on the ``Vote``, and that all its fields are up to date.
    """
    common_columns = (set(VoteRecord.__table__.columns.keys())
                      .intersection(set(Vote.__table__.columns.keys())))

    def _assert_record(target):
        if not target.record:
            target.record = VoteRecord()

    def _set_value(target, value):
        setattr(target.record, target_column, value)

    def _copy_columns(target):
        for column in common_columns.difference((target_column, )):
            setattr(target.record, column, getattr(target, column))

    def updater(target, value, oldvalue, initiator):
        if oldvalue in (NO_VALUE, NEVER_SET):
            # We're setting an initial value. This means that we just need to
            # ensure that an initial VoteRecord exists, and then mutate it
            # directly.
            _assert_record(target)
            _set_value(target, value)
        elif value != oldvalue:
            # We're *altering* a Vote value. This means that we must create a
            # *new* VoteRecord, and copy all the *other* fields from the Vote,
            # then update it with the new value.
            target.record = VoteRecord()
            _copy_columns(target)
            _set_value(target, value)
        else:
            # The value hasn't changed -- we don't really need to do anything,
            # but we ensure that a VoteRecord exists for the Vote object.
            _assert_record(target)
    return updater


vote_record_data = Datasource('ip_addr', 'user')
sqlalchemy.event.listen(Vote.ballot_id, 'set', vote_record_copy('ballot_id'))
sqlalchemy.event.listen(Vote.voter_id, 'set', vote_record_copy('voter_id'))
sqlalchemy.event.listen(VoteRecord, 'before_insert',
                        vote_record_data.before_insert_handler)
