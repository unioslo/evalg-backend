import pytest

from evalg.authorization import (allows,
                                 PermissionDenied)
from evalg.authorization import permissions
from evalg.proc.authz import get_or_create_principal, add_election_group_role


def test_requirements_throw_PermissionDenied_on_deny(
        db_session, logged_in_user, election_group_foo):
    with pytest.raises(PermissionDenied):
        allows.run([
            permissions.IsElectionGroupAdmin(
                session=db_session,
                election_group_id=election_group_foo.id)
        ])


def test_can_manage_election_group_denies(
        db_session, logged_in_user, election_group_foo):
    assert not permissions.Permissions.can_manage_election_group(
        session=db_session,
        user=logged_in_user,
        election_group_id=election_group_foo.id)


def test_can_manage_election_group_allows(
        db_session, logged_in_user, election_group_foo):
    principal = get_or_create_principal(
        db_session, 'person', person_id=logged_in_user.person.id)
    add_election_group_role(
        db_session,
        election_group=election_group_foo,
        principal=principal,
        role_name='admin')
    assert permissions.Permissions.can_manage_election_group(
        session=db_session,
        user=logged_in_user,
        election_group_id=election_group_foo.id)
