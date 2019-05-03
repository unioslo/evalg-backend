"""
GraphQL ObjectType for authorization roles.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.authorization
from evalg import db

from . import person
from . import group


#
# Queries
#

# TODO:
#   We should rework the authorization a bit - That may change the models here.

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   evalg.candidates in order to show or mutate candidate lists or candidates.


class Principal(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.Principal

    person = graphene.Field(person.Person)
    group = graphene.Field(group.Group)


class PersonPrincipal(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.PersonPrincipal


class GroupPrincipal(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.GroupPrincipal


# class ElectionRole(graphene_sqlalchemy.SQLAlchemyObjectType):
#     class Meta:
#         model = evalg.models.authorization.ElectionRole


# class ElectionRoleList(graphene_sqlalchemy.SQLAlchemyObjectType):
#     class Meta:
#         model = evalg.models.authorization.ElectionRoleList


class ElectionGroupRole(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.ElectionGroupRole


#
# Mutations
#


class AddAdmin(graphene.Mutation):
    """
    Add a user as administrator to a given election group.
    """
    class Arguments:
        admin_id = graphene.UUID(required=True)
        el_grp_id = graphene.UUID(required=True)
        type = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        # TODO:
        #   We should rework the argument names in these queries.
        #   *admin_id*? *el_grp_id*?
        # TODO:
        #   Should we check if the Principal objects already exists?
        if args.get('type') == 'person':
            principal = evalg.models.authorization.PersonPrincipal(
                person_id=args.get('admin_id'))
        else:
            principal = evalg.models.authorization.GroupPrincipal(
                group_id=args.get('admin_id'))
        role = evalg.models.authorization.ElectionGroupRole(
            role='election-admin',
            principal=principal,
            group_id=args.get('el_grp_id'))
        db.session.add(role)
        db.session.commit()
        return AddAdmin(ok=True)


class RemoveAdmin(graphene.Mutation):
    """
    Remove a an administrative role from a given election group.
    """
    class Arguments:
        grant_id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        # TODO:
        #   Where do we get the grant_id from? Are we missing some queries?
        role = evalg.models.authorization.ElectionGroupRole.query.get(
            args.get('grant_id'))
        db.session.delete(role)
        db.session.commit()
        return RemoveAdmin(ok=True)
