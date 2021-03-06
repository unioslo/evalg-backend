"""
This module contains functionality for applying permission control to graphql
fields and mutations.
"""
import logging
import functools

from flask import current_app

from graphene.types.resolver import get_default_resolver
from flask_sqlalchemy.model import camel_to_snake_case
from flask_allows import Permission

from evalg.proc.pollbook import get_voters_for_person
from evalg.utils import Name2Callable
from evalg.models.election_list import ElectionList
from evalg.models.election import ElectionGroup
from evalg.graphql.nodes.utils.base import (get_session,
                                            get_current_user)
from evalg.authorization.permissions import (IsElectionGroupAdmin,
                                             IsPerson,
                                             HasPersonCreatedMyElectionsKey,
                                             IsPublisher,
                                             IsVoter)

all_permissions = Name2Callable()
logger = logging.getLogger(__name__)


@all_permissions
def deny(*args, **kwargs):
    return False


@all_permissions
def allow(*args, **kwargs):
    return True


@all_permissions
def can_manage_election_group(session, user, election_group, **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, election_group.id),
        identity=user)


@all_permissions
def can_publish_election_groups(session, user, **kargs):
    return Permission(
        IsPublisher(session),
        identity=user)


@all_permissions
def can_manage_election(session, user, election, **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, election.group_id),
        identity=user
    )


@all_permissions
def can_manage_pollbook(session, user, pollbook, **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, pollbook.election.group_id),
        identity=user
    )


@all_permissions
def can_manage_census_file_upload(session, user, census_file_upload, **kwargs):
    return Permission(
        IsElectionGroupAdmin(
            session, census_file_upload.pollbook.election.group_id),
        identity=user
    )


@all_permissions
def can_manage_election_list(session, user, **kwargs):
    if 'list_id' in kwargs:
        election_list = session.query(ElectionList).get(kwargs.get('list_id'))
        return Permission(
            IsElectionGroupAdmin(session, election_list.election.group_id),
            identity=user
        )
    return False


@all_permissions
def can_access_election_result(session, user, election_result, **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, election_result.election.group_id),
        identity=user)


@all_permissions
def can_access_election_group_count(session,
                                    user,
                                    election_group_count,
                                    **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, election_group_count.group_id),
        identity=user
    )


@all_permissions
def can_view_election_group_key_meta(session,
                                     user,
                                     election_key_meta,
                                     **kwargs):
    return Permission(
        IsElectionGroupAdmin(session, election_key_meta.election_group_id),
        identity=user)


@all_permissions
def can_view_person(session, user, person, **kwargs):
    if Permission(IsPerson(person), identity=user):
        return True
    voters = get_voters_for_person(session, person).all()
    for voter in voters:
        if Permission(
                IsElectionGroupAdmin(session,
                                     voter.pollbook.election.group_id),
                identity=user):
            return True
    if Permission(HasPersonCreatedMyElectionsKey(session, person),
                  identity=user):
        return True
    return False


@all_permissions
def can_view_person_ids(session, user, person_ids, **kwargs):
    if Permission(IsPerson(person_ids.person), identity=user):
        return True
    voters = get_voters_for_person(session, person_ids.person).all()
    for voter in voters:
        if Permission(
                IsElectionGroupAdmin(session,
                                     voter.pollbook.election.group_id),
                identity=user):
            return True
    if Permission(HasPersonCreatedMyElectionsKey(session, person_ids.person),
                  identity=user):
        return True
    return False


@all_permissions
def can_manage_voter(session, user, voter, **kwargs):
    if Permission(
            IsElectionGroupAdmin(session, voter.pollbook.election.group_id),
            identity=user):
        return True
    return False


@all_permissions
def can_view_voter(session, user, voter, **kwargs):
    if Permission(
            IsElectionGroupAdmin(session, voter.pollbook.election.group_id),
            identity=user):
        return True
    if Permission(IsVoter(session, voter), identity=user):
        return True
    return False


@all_permissions
def can_vote(session, user, voter, **kwargs):
    return Permission(IsVoter(session, voter), identity=user)


@all_permissions
def can_view_vote(session, user, vote, **kwargs):
    return Permission(IsVoter(session, vote.voter), identity=user)


@functools.lru_cache(maxsize=1)
def permissions_config():
    return current_app.config.get('PERMISSIONS')


def can_access_field(source, info, **kwargs):
    """Checks if the requested field can be accessed by the user

    :type info: graphql.execution.base.ResolveInfo
    """
    session = get_session(info)
    user = get_current_user(info)
    permissions = permissions_config().get(str(info.parent_type))
    if permissions is None:
        return False
    field_name = camel_to_snake_case(info.field_name)
    permission = permissions.get(field_name)
    if all_permissions.get(permission, deny)(session, user, source,
                                             path=info.path, **kwargs):
        return True
    return False


class PermissionController(object):
    """
    Class for adding permission control to ObjectTypes and Fields, and keep
    track of which Fields have been controlled.
    """

    def __init__(self):
        self.fields_cache = []
        self.controlled_fields = {}

    def __call__(self, resolver):
        """Decorator which adds permission control to a resolver

         :type resolver: function
         """
        self.fields_cache.append(resolver.__name__)

        @functools.wraps(resolver)
        def wrapper(source, info, **kwargs):
            if can_access_field(source, info, **kwargs):
                return resolver(source, info, **kwargs)
            return None

        return wrapper

    def control_object_type(self, object_type):
        """Class decorator which helps keep track of controlled fields

        :type object_type: subclass of SQLAlchemyObjectType
        """
        self.controlled_fields[object_type.__name__] = self.fields_cache
        self.fields_cache = []
        return object_type


permission_controller = PermissionController()


def permission_controlled_default_resolver(attname,
                                           default_value,
                                           root,
                                           info,
                                           **kwargs):
    if can_access_field(root, info, **kwargs):
        return get_default_resolver()(attname,
                                      default_value,
                                      root,
                                      info,
                                      **kwargs)
    return None
