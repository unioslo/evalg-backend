"""
Database models for elections.
"""
import uuid

from sqlalchemy.sql import select, func, case, and_
from sqlalchemy.ext.hybrid import hybrid_property

import evalg.database.types
from evalg import db
from evalg.utils import utcnow
from .base import ModelBase


class AbstractElection(ModelBase):
    """ Base model for elections and election groups. """

    __abstract__ = True

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)
    """ Election id """

    name = db.Column(evalg.database.types.MutableJson)
    """ Translated name """

    description = db.Column(evalg.database.types.MutableJson)
    """ Translated text """

    type = db.Column(db.UnicodeText)
    """ Internal use """

    meta = db.Column(evalg.database.types.NestedMutableJson)
    """ Template metadata """


class ElectionGroup(AbstractElection):

    __versioned__ = {}

    ou_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('organizational_unit.id'),
        nullable=True)

    ou = db.relationship('OrganizationalUnit')

    elections = db.relationship('Election')
    """ Organizational unit. """

    election_group_counts = db.relationship('ElectionGroupCount')

    public_key = db.Column(db.Text)
    """ Public election key """

    announced_at = db.Column(evalg.database.types.UtcDateTime)
    """ Announced if set """

    published_at = db.Column(evalg.database.types.UtcDateTime)
    """ Published if set """

    cancelled_at = db.Column(evalg.database.types.UtcDateTime)
    """ Cancelled if set """

    deleted_at = db.Column(evalg.database.types.UtcDateTime)
    """ Deleted if set """

    def announce(self):
        """ Mark as announced. """
        self.announced_at = utcnow()

    def unannounce(self):
        """ Mark as unannounced. """
        self.announced_at = None

    @hybrid_property
    def announced(self):
        return self.announced_at is not None

    def publish(self):
        """ Mark as published. """
        self.published_at = utcnow()

    def unpublish(self):
        """ Mark as unpublished. """
        self.published_at = None

    @hybrid_property
    def published(self):
        return self.published_at is not None

    def cancel(self):
        """ Mark as cancelled. """
        self.cancelled_at = utcnow()

    @hybrid_property
    def cancelled(self):
        return self.cancelled_at is not None

    def delete(self):
        """ Mark as deleted. """
        self.deleted_at = utcnow()

    @hybrid_property
    def deleted(self):
        return self.deleted_at is not None

    @hybrid_property
    def status(self):
        statuses = set(list(map(lambda x: x.status, self.elections)))
        if not statuses:
            return 'draft'
        if len(statuses) == 1:
            return statuses.pop()
        return 'multipleStatuses'

    # @status.expression
    # def status(cls):
    #     # TODO: make expression
    #     return ''


class Election(AbstractElection):
    """ Election. """

    __versioned__ = {}

    sequence = db.Column(db.Text)
    """ Some ID for the UI """

    start = db.Column(evalg.database.types.UtcDateTime)

    end = db.Column(evalg.database.types.UtcDateTime)

    information_url = db.Column(evalg.database.types.UrlType)

    contact = db.Column(db.Text)

    mandate_period_start = db.Column(db.Date)

    mandate_period_end = db.Column(db.Date)

    group_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('election_group.id'))

    election_group = db.relationship(
        'ElectionGroup',
        back_populates='elections',
        lazy='joined')

    election_results = db.relationship('ElectionResult')

    lists = db.relationship('ElectionList')

    pollbooks = db.relationship('PollBook')

    active = db.Column(db.Boolean, default=False)
    """ Whether election is active.
    We usually create more elections than needed to make templates consistent.
    But not all elections should be used. This can improve voter UI, by telling
    voter that their group does not have an active election. """

    @hybrid_property
    def announced_at(self):
        return self.election_group.announced_at

    @announced_at.expression
    def announced_at(cls):
        return select([ElectionGroup.announced_at]).where(
            cls.group_id == ElectionGroup.id).as_scalar()

    @hybrid_property
    def published_at(self):
        return self.election_group.published_at

    @published_at.expression
    def published_at(cls):
        return select([ElectionGroup.published_at]).where(
            cls.group_id == ElectionGroup.id).as_scalar()

    @hybrid_property
    def cancelled_at(self):
        return self.election_group.cancelled_at

    @cancelled_at.expression
    def cancelled_at(cls):
        return select([ElectionGroup.cancelled_at]).where(
            cls.group_id == ElectionGroup.id).as_scalar()

    @hybrid_property
    def status(self):
        """ draft → announced → published → ongoing/closed/cancelled """
        if self.election_group.cancelled_at:
            return 'cancelled'
        if self.election_group.published_at:
            if self.end <= utcnow():
                return 'closed'
            if self.start <= utcnow():
                return 'ongoing'
            return 'published'
        if self.election_group.announced_at:
            return 'announced'
        return 'draft'

    @status.expression
    def status(cls):
        return case([
            (cls.cancelled_at.isnot(None), 'cancelled'),
            (and_(cls.published_at.isnot(None),
                  cls.end <= func.now()), 'closed'),
            (and_(cls.published_at.isnot(None),
                  cls.start <= func.now()), 'ongoing'),
            (cls.published_at.isnot(None), 'published'),
            (cls.announced_at.isnot(None), 'announced')],
            else_='draft')

    @hybrid_property
    def has_started(self):
        """ Check if an election is past its start time. """
        return bool(self.start and self.start <= utcnow())

    @has_started.expression
    def has_started(cls):
        return case([
            (and_(cls.start.isnot(None),
                  cls.start <= func.now()), True)],
            else_=False)

    @hybrid_property
    def is_ongoing(self):
        """ Check if an election is currently ongoing. """
        return bool(self.election_group.published_at and
                    self.start <= utcnow() and
                    self.end >= utcnow())

    @is_ongoing.expression
    def is_ongoing(cls):
        return case([
            (and_(cls.published_at.isnot(None),
                  cls.start.isnot(None),
                  cls.start <= func.now(),
                  cls.end.isnot(None),
                  cls.end >= func.now()), True)],
            else_=False)

    @property
    def ou_id(self):
        return self.election_group.ou_id

    @property
    def ou(self):
        return self.election_group.ou

    @property
    def list_ids(self):
        return [l.id for l in self.lists if not l.deleted]
