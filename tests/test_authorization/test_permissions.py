import pytest

from evalg.authorization import (allows,
                                 PermissionDenied)
from evalg.graphql.nodes.utils import permissions
from evalg.proc.authz import (get_or_create_principal, add_election_group_role)


def test_requirements_throw_PermissionDenied_on_deny(
        db_session,
        election_group_generator):
    election_group = election_group_generator()
    with pytest.raises(PermissionDenied):
        allows.run([
            permissions.IsElectionGroupAdmin(
                session=db_session,
                election_group_id=election_group.id)
        ])


def test_can_manage_election_group_denies(
        db_session,
        logged_in_user,
        election_group_generator):
    election_group = election_group_generator()
    assert not permissions.can_manage_election_group(
        session=db_session,
        user=logged_in_user,
        election_group=election_group)


def test_can_manage_election_group_allows(
        db_session,
        logged_in_user,
        election_group_generator):
    election_group = election_group_generator(owner=True)
    principal = get_or_create_principal(
        db_session, 'person', person_id=logged_in_user.person.id)
    add_election_group_role(
        db_session,
        election_group=election_group,
        principal=principal,
        role_name='admin')
    assert permissions.can_manage_election_group(
        session=db_session,
        user=logged_in_user,
        election_group=election_group)


def test_can_publish_election_allows(db_session,
                                     logged_in_user,
                                     make_group_membership,
                                     global_roles):
    """Test that we need the publisher role to publish."""
    publisher_group = global_roles['publisher']['group']
    make_group_membership(db_session, publisher_group, logged_in_user.person)
    assert permissions.can_publish_election_groups(
        session=db_session,
        user=logged_in_user
    )


def test_can_publish_election_denies(db_session,
                                     logged_in_user,
                                     global_roles):
    """Test that we need the publisher role to publish."""
    assert not permissions.can_publish_election_groups(
        session=db_session,
        user=logged_in_user
    )
