""" evalg graphql api. """
import graphene
from flask_graphql import GraphQLView
from graphene.types.generic import GenericScalar
from graphene import Argument

from evalg.election_templates import election_template_builder
from evalg.utils import convert_json
from evalg.group import search_group
from evalg.person import search_person

from . import entities
from . import mutations


class Query(graphene.ObjectType):
    elections = graphene.List(entities.Election)

    def resolve_elections(self, info):
        return entities.Election.get_query(info).all()

    election = graphene.Field(
        entities.Election,
        id=Argument(graphene.UUID, required=True))

    def resolve_election(self, info, **args):
        return entities.Election.get_query(info).get(args.get('id'))

    election_groups = graphene.List(entities.ElectionGroup)

    def resolve_election_groups(self, info):
        return entities.ElectionGroup.get_query(info).all()

    election_group = graphene.Field(
        entities.ElectionGroup,
        id=Argument(graphene.UUID, required=True))

    def resolve_election_group(self, info, **args):
        return entities.ElectionGroup.get_query(info).get(args.get('id'))

    election_lists = graphene.List(entities.ElectionList)

    def resolve_election_lists(self, info, **args):
        return entities.ElectionList.get_query.all()

    election_list = graphene.Field(
        entities.ElectionList,
        id=Argument(graphene.UUID, required=True))

    def resolve_election_list(self, info, **args):
        return entities.ElectionList.get_query(info).get(args.get('id'))

    candidates = graphene.List(entities.Candidate)

    def resolve_candidates(self, info):
        return entities.Candidate.get_query(info).all()

    candidate = graphene.Field(
        entities.Candidate,
        id=Argument(graphene.UUID, required=True))

    def resolve_candidate(self, info, **args):
        return entities.Candidate.get_query(info).get(args.get('id'))

    persons = graphene.List(entities.Person)

    def resolve_persons(self, info):
        return entities.Person.get_query(info).all()

    person = graphene.Field(
        entities.Person,
        id=Argument(graphene.UUID, required=True))

    def resolve_person(self, info, **args):
        return entities.Person.get_query(info).get(args.get('id'))

    pollbooks = graphene.List(entities.PollBook)

    def resolve_pollbooks(self, info):
        return entities.PollBook.get_query(info).all()

    pollbook = graphene.Field(
        entities.PollBook,
        id=Argument(graphene.UUID, required=True))

    def resolve_pollbook(self, info, **args):
        return entities.PollBook.get_query(info).get(args.get('id'))

    voters = graphene.List(entities.Voter)

    def resolve_voters(self, info):
        return entities.Voter.get_query(info).all()

    voter = graphene.Field(
        entities.Voter,
        id=Argument(graphene.UUID, required=True))

    def resolve_voter(self, info, **args):
        return entities.Voter.get_query(info).get(args.get('id'))

    election_template = graphene.Field(GenericScalar)

    def resolve_election_template(self, info, **args):
        template = election_template_builder()
        return convert_json(template)

    search_persons = graphene.List(
        entities.Person,
        val=Argument(graphene.String, required=True))

    def resolve_search_persons(self, info, **args):
        return search_person(args.get('val'))

    search_groups = graphene.List(
        entities.Group,
        val=Argument(graphene.String, required=True))

    def resolve_search_groups(self, info, **args):
        return search_group(args.get('val'))


schema = graphene.Schema(
    query=Query,
    mutation=mutations.Mutations,
    types=[entities.ElectionGroup])


def init_app(app):
    from evalg.graphql.middleware import timing_middleware, auth_middleware

    middleware = [timing_middleware]
    if app.config.get('AUTH_ENABLED'):
        middleware.append(auth_middleware)

    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            batch=True,
            graphiql=True,
            middleware=middleware
        ))
