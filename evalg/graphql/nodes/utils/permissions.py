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
def can_manage_election_group(session, user, election_group, **args):
    return Permission(
        IsElectionGroupAdmin(session, election_group.id),
        identity=user)


@all_permissions
def can_publish_election_groups(session, user, **kargs):
    return Permission(
        IsPublisher(session),
        identity=user)


@all_permissions
def can_manage_election(session, user, election, **args):
    return Permission(
        IsElectionGroupAdmin(session, election.group_id),
        identity=user
    )


@all_permissions
def can_manage_pollbook(session, user, pollbook, **args):
    return Permission(
        IsElectionGroupAdmin(session, pollbook.election.group_id),
        identity=user
    )


@all_permissions
def can_manage_election_list(session, user, **args):
    if 'list_id' in args:
        election_list = session.query(ElectionList).get(args.get('list_id'))
        return Permission(
            IsElectionGroupAdmin(session, election_list.election.group_id),
            identity=user
        )
    return False


@all_permissions
def can_access_election_result(session, user, election_result, **args):
    return Permission(
        IsElectionGroupAdmin(session, election_result.election.group_id),
        identity=user)


@all_permissions
def can_access_election_group_count(session,
                                    user,
                                    election_group_count,
                                    **args):
    return Permission(
        IsElectionGroupAdmin(session, election_group_count.group_id),
        identity=user
    )


@all_permissions
def can_view_person(session, user, person, **args):
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
def can_manage_voter(session, user, voter, **args):
    if Permission(IsVoter(session, voter), identity=user):
        return True
    if Permission(
            IsElectionGroupAdmin(session, voter.pollbook.election.group_id),
            identity=user):
        return True
    return False


@all_permissions
def can_vote(session, user, voter, **args):
    return Permission(IsVoter(session, voter), identity=user)


@all_permissions
def can_view_vote(session, user, vote, **args):
    return Permission(IsVoter(session, vote.voter), identity=user)


@functools.lru_cache(maxsize=1)
def permissions_config():
    return current_app.config.get('PERMISSIONS')


def can_access_field(source, info, **args):
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
                                             path=info.path, **args):
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
        def wrapper(source, info, **args):
            if can_access_field(source, info, **args):
                return resolver(source, info, **args)
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


def permission_controlled_default_resolver(attname, default_value, root, info,
                                           **args):
    if can_access_field(root, info, **args):
        return get_default_resolver()(attname, default_value, root, info,
                                      **args)
    return None
