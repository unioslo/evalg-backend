"""
The GraphQL ElectionGroup ObjectType.

This module defines the GraphQL ObjectType that represents election group, as
well as queries and mutations for this object.
"""
import graphene
import graphene_sqlalchemy
from graphene.types.generic import GenericScalar

import evalg.metadata
import evalg.models.election
from evalg import db
from evalg.election_templates import election_template_builder
from evalg.utils import convert_json


# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   elsewhere.


#
# Query
#


class ElectionGroup(graphene_sqlalchemy.SQLAlchemyObjectType):
    """
    A group of elections.
    """
    class Meta:
        model = evalg.models.election.ElectionGroup

    def resolve_meta(self, info):
        return convert_json(self.meta)

    announcement_blockers = graphene.List(graphene.String)
    publication_blockers = graphene.List(graphene.String)
    published = graphene.Boolean()
    announced = graphene.Boolean()

    def resolve_announcement_blockers(self, info):
        return evalg.metadata.group_announcement_blockers(self)

    def resolve_publication_blockers(self, info):
        return evalg.metadata.group_publication_blockers(self)


def resolve_election_groups_by_fields(_, info):
    return ElectionGroup.get_query(info).all()


def resolve_election_group_by_id(_, info, **args):
    return ElectionGroup.get_query(info).get(args['id'])


list_election_groups_query = graphene.List(
    ElectionGroup,
    resolver=resolve_election_groups_by_fields)


get_election_group_query = graphene.Field(
    ElectionGroup,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_group_by_id)


# TODO:
#   Election templates should *probably* have more structured output.


def resolve_election_template(_, info, **args):
    template = election_template_builder()
    return convert_json(template)


get_election_template_query = graphene.Field(
    GenericScalar,
    resolver=resolve_election_template)


#
# Mutation
#


class CreateNewElectionGroup(graphene.Mutation):
    """
    Create an ElectionGroup from a template.
    """
    class Arguments:
        ou_id = graphene.UUID()
        template = graphene.Boolean()
        template_name = graphene.String()

    ok = graphene.Boolean()
    election_group = graphene.Field(lambda: ElectionGroup)

    def mutate(self, info, ou_id, template, template_name):
        # TODO: Looks like template_name is required?
        ou = evalg.models.ou.OrganizationalUnit.query.get(ou_id)
        election_group = evalg.metadata.make_group_from_template(template_name,
                                                                 ou)
        return CreateNewElectionGroup(
            election_group=election_group,
            ok=True)


class ElectionBaseSettingsInput(graphene.InputObjectType):
    """
    Individual settings input for elections in an election group.
    """
    id = graphene.UUID(required=True)
    seats = graphene.Int(required=True)
    substitutes = graphene.Int(required=True)
    active = graphene.Boolean(required=True)


class UpdateBaseSettings(graphene.Mutation):
    """
    Update settings for elections in an election group.
    """
    class Arguments:
        id = graphene.UUID(required=True)
        elections = graphene.List(ElectionBaseSettingsInput, required=True)
        has_gender_quota = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        # TODO:
        #   Is there any particular reason why the ElectionGroup settings and
        #   Election settings are bound together in a single mutation?
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        el_grp.meta['candidate_rules']['candidate_gender'] =\
            args.get('has_gender_quota')
        db.session.add(el_grp)
        for e in args.get('elections'):
            election = evalg.models.election.Election.query.get(e['id'])
            election.meta['candidate_rules']['seats'] = e.seats
            election.meta['candidate_rules']['substitutes'] = e.substitutes
            election.active = e.active
            db.session.add(election)
        db.session.commit()
        return UpdateBaseSettings(ok=True)


class PublishElectionGroup(graphene.Mutation):
    """
    Publish an ElectionGroup.
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        evalg.metadata.publish_group(el_grp)
        return PublishElectionGroup(ok=True)


class UnpublishElectionGroup(graphene.Mutation):
    """
    Unpublish an ElectionGroup.
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        evalg.metadata.unpublish_group(el_grp)
        return UnpublishElectionGroup(ok=True)


class AnnounceElectionGroup(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        evalg.metadata.announce_group(el_grp)
        return AnnounceElectionGroup(ok=True)


class UnannounceElectionGroup(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        evalg.metadata.unannounce_group(el_grp)
        return UnannounceElectionGroup(ok=True)


class CreateElectionGroupKey(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        key = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = evalg.models.election.ElectionGroup.query.get(args.get('id'))
        el_grp.public_key = args.get('key')
        db.session.add(el_grp)
        db.session.commit()
        return CreateElectionGroupKey(ok=True)
