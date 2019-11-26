"""
Database models for elections.
"""
import math
import uuid

from sqlalchemy.sql import select, func, case, and_
from sqlalchemy.ext.hybrid import hybrid_property

import evalg.database.types
from evalg import db
from evalg.utils import utcnow
from .base import ModelBase


class QuotaGroup:
    """The candidate quota-group class"""

    def __init__(self, name, members, min_value, min_value_substitutes=0):
        """
        Keyword Arguments:
        :param name: The name of the quota-group
        :type name: str or dict

        :param members: The sequence of candidates
        :type members: collections.abc.Sequence

        :param min_value: The min. value
        :type min_value: int

        :param min_value_substitutes: The min. value for substitutes (if any)
        :type min_value_substitutes: int
        """
        self.name = name
        self.members = tuple(members)
        self.min_value = min_value
        self.min_value_substitutes = min_value_substitutes

    def __str__(self):
        """Used for debugging"""
        return '{name}({min_value}, {min_value_substitutes})'.format(
            name=self.name,
            min_value=self.min_value,
            min_value_substitutes=self.min_value_substitutes)


class AbstractElection(ModelBase):
    """ Base model for elections and election groups. """

    __abstract__ = True

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    # Translated name
    name = db.Column(evalg.database.types.MutableJson)

    # Translated text
    description = db.Column(evalg.database.types.MutableJson)

    # Template metadata
    meta = db.Column(evalg.database.types.NestedMutableJson)


class ElectionGroup(AbstractElection):

    __versioned__ = {}

    ou_id = db.Column(
        evalg.database.types.UuidType,
        db.ForeignKey('organizational_unit.id'),
        nullable=True)

    ou = db.relationship('OrganizationalUnit')

    # Organizational unit
    elections = db.relationship('Election')

    election_group_counts = db.relationship('ElectionGroupCount')

    # Public election key
    public_key = db.Column(db.Text)

    # Announced if set
    announced_at = db.Column(evalg.database.types.UtcDateTime)

    # Published if set
    published_at = db.Column(evalg.database.types.UtcDateTime)

    # Cancelled if set
    cancelled_at = db.Column(evalg.database.types.UtcDateTime)

    # Deleted if set
    deleted_at = db.Column(evalg.database.types.UtcDateTime)

    # Name of the template used to create the election group
    template_name = db.Column(db.UnicodeText)

    # Internal use
    type = db.Column(db.UnicodeText)

    def announce(self):
        """Mark as announced."""
        self.announced_at = utcnow()

    def unannounce(self):
        """Mark as unannounced."""
        self.announced_at = None

    @hybrid_property
    def announced(self):
        return self.announced_at is not None

    @announced.expression
    def announced(cls):
        return cls.announced_at.isnot(None)

    def publish(self):
        """Mark as published."""
        self.published_at = utcnow()

    def unpublish(self):
        """Mark as unpublished."""
        self.published_at = None

    @hybrid_property
    def published(self):
        return self.published_at is not None

    @published.expression
    def published(cls):
        return cls.published_at.isnot(None)

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
        if len(statuses) == 2 and 'inactive' in statuses:
            statuses.discard('inactive')
            return statuses.pop()
        return 'multipleStatuses'


class Election(AbstractElection):
    """ Election. """

    __versioned__ = {}

    # Some ID for the UI
    sequence = db.Column(db.Text)

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

    pollbooks = db.relationship('Pollbook')

    # Whether election is active.
    # We usually create more elections than needed to make templates consistent
    # But not all elections should be used. This can improve voter UI, by
    # telling voter that their group does not have an active election.
    active = db.Column(db.Boolean, default=False)

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
        """
        inactive → draft → announced → published → ongoing/closed/cancelled
        """
        if not self.active:
            return 'inactive'
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
            (cls.active is False, 'inactive'),
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
        """Check if an election is past its start time."""
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

    @property
    def num_choosable(self):
        return self.meta['candidate_rules']['seats']

    @property
    def num_substitutes(self):
        return self.meta['candidate_rules'].get('substitutes', 0)

    @property
    def candidates(self):
        if len(self.lists) > 1:
            raise Exception('Not intended for use on election with '
                            'with multiple candidate lists')
        return self.lists[0].candidates

    @property
    def quotas(self):
        quotas = []
        if self.meta['candidate_rules'].get('candidate_gender'):
            quota_names = self.meta['counting_rules']['affirmative_action']
            for quota_name in quota_names:
                if quota_name == 'gender_40':  # the only one supported so far
                    males = []
                    females = []
                    min_value = 0
                    min_value_substitutes = 0  # for uiostv .. etc
                    for candidate in self.candidates:
                        if candidate.meta['gender'] == 'male':
                            males.append(candidate)
                        elif candidate.meta['gender'] == 'female':
                            females.append(candidate)
                    if self.type_str == 'uio_stv':
                        # no other elections implemented yet...
                        if self.num_choosable <= 1:
                            min_value = 0
                        elif self.num_choosable <= 3:
                            min_value = 1
                        elif self.num_choosable:
                            min_value = math.ceil(0.4 * self.num_choosable)
                        if self.num_substitutes <= 1:
                            min_value_substitutes = 0
                        elif self.num_substitutes <= 3:
                            min_value_substitutes = 1
                        elif self.num_substitutes:
                            min_value_substitutes = math.ceil(
                                0.4 * self.num_substitutes)
                    # handle universal cases when members < min_value
                    min_value_males = min([min_value, len(males)])
                    min_value_females = min([min_value, len(females)])
                    quotas.append(
                        QuotaGroup(
                            {'en': 'Males',
                             'nn': 'Menn',
                             'nb': 'Menn'},
                            males,
                            min_value_males,
                            min([min_value_substitutes,
                                 len(males) - min_value_males])))
                    quotas.append(
                        QuotaGroup(
                            {'en': 'Females',
                             'nn': 'Kvinner',
                             'nb': 'Kvinner'},
                            females,
                            min_value_females,
                            min([min_value_substitutes,
                                 len(females) - min_value_females])))

        return quotas

    @property
    def type_str(self):
        """type_str-property"""
        return self.meta['counting_rules']['method']
