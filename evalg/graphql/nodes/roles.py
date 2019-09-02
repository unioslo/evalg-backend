"""
GraphQL ObjectType for authorization roles.
"""
import graphene
import graphene_sqlalchemy

import evalg.database.query
import evalg.models.authorization
from evalg.graphql.types import PersonIdType, ElectionGroupRoleType
from evalg.graphql.nodes.base import (get_session,
                                      get_current_user,
                                      MutationResponse)
from evalg.proc.authz import (get_or_create_principal,
                              add_election_group_role,
                              delete_role)
from evalg.authorization.permissions import Permissions

#
# Queries
#


class PersonPrincipal(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.PersonPrincipal
        exclude_fields = ('principal_type', )


class PersonIdentifierPrincipal(graphene_sqlalchemy.SQLAlchemyObjectType):
    id_type = PersonIdType(required=True)

    class Meta:
        model = evalg.models.authorization.PersonIdentifierPrincipal
        exclude_fields = ('principal_type', )


class GroupPrincipal(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.GroupPrincipal
        exclude_fields = ('principal_type', )


class Principal(graphene.types.Union):
    class Meta:
        types = (PersonPrincipal, PersonIdentifierPrincipal, GroupPrincipal)


class ElectionGroupRole(graphene_sqlalchemy.SQLAlchemyObjectType):
    principal = graphene.Field(Principal)

    class Meta:
        model = evalg.models.authorization.ElectionGroupRole
        exclude_fields = ('target_type', )


class Role(graphene.types.Union):
    class Meta:
        types = (ElectionGroupRole, )


#
# Mutations
#

class AddElectionGroupRoleByIdentifierResponse(MutationResponse):
    pass


class AddElectionGroupRoleByIdentifier(graphene.Mutation):
    """
    Add an election group role to a user identifier.
    """
    class Arguments:
        election_group_id = graphene.UUID(required=True)
        role = ElectionGroupRoleType(required=True)
        id_type = PersonIdType(required=True)
        id_value = graphene.String(required=True)

    Output = AddElectionGroupRoleByIdentifierResponse

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        election_group_id = args.get('election_group_id')
        role_name = args.get('role')
        id_type = args.get('id_type')
        id_value = args.get('id_value')
        election_group = evalg.database.query.lookup_or_none(
            session,
            evalg.models.election.ElectionGroup,
            id=election_group_id)
        if election_group is None:
            return AddElectionGroupRoleByIdentifierResponse(
                success=False,
                code='election-group-not-found',
                message='No election group identified by {}'.format(
                    election_group_id)
            )
        if not Permissions.can_manage_election_group(session, user,
                                                     election_group.id):
            return AddElectionGroupRoleByIdentifierResponse(
                success=False,
                code='permission-denied',
                message='Not allowed to add roles for election {}'.format(
                    election_group_id)
            )
        principal = get_or_create_principal(
            session=session,
            principal_type='person_identifier',
            id_type=id_type,
            id_value=id_value)
        add_election_group_role(
            session=session,
            election_group=election_group,
            principal=principal,
            role_name=role_name)
        session.commit()
        return AddElectionGroupRoleByIdentifierResponse(
            success=True,
            code='role-added')


class RemoveElectionGroupRoleByGrantResponse(MutationResponse):
    pass


class RemoveElectionGroupRoleByGrant(graphene.Mutation):
    """
    Add an election group role by the grant ID.
    """
    class Arguments:
        grant_id = graphene.UUID(required=True)

    Output = RemoveElectionGroupRoleByGrantResponse

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        grant_id = args.get('grant_id')
        role = evalg.proc.authz.get_role_by_grant_id(session, grant_id)
        if role is None:
            return RemoveElectionGroupRoleByGrantResponse(
                success=False,
                code='grant-not-found',
                message='No election group role grant identified by {}'.format(
                    grant_id)
            )
        if not Permissions.can_manage_election_group(session, user, role.group.id):
            return RemoveElectionGroupRoleByGrantResponse(
                success=False,
                code='permission-denied',
                message='Not allowed to remove roles for election {}'.format(
                    role.group.id)
            )
        delete_role(session, role)
        session.commit()
        return RemoveElectionGroupRoleByGrantResponse(
            success=True,
            code='role-removed')
