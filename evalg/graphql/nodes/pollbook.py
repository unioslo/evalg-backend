"""
GraphQL ObjectType for PollBook and Voter nodes.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.election
import evalg.models.pollbook
import evalg.models.voter
from evalg import db


#
# Query
#


# TODO/TBD:
#   Could we rename PollBook to Pollbook?

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   elsewhere in order to show or mutate objects. The business logic should not
#   be tied to GraphQL.

class PollBook(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.pollbook.PollBook


def resolve_pollbooks_by_fields(_, info):
    return PollBook.get_query(info).all()


def resolve_pollbook_by_id(_, info, **args):
    return PollBook.get_query(info).get(args['id'])


list_pollbooks_query = graphene.List(
    PollBook,
    resolver=resolve_pollbooks_by_fields)

get_pollbook_query = graphene.Field(
    PollBook,
    resolver=resolve_pollbook_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


class Voter(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.voter.Voter


def resolve_voters_by_fields(_, info):
    return Voter.get_query(info).all()


def resolve_voter_by_id(_, info, **args):
    return Voter.get_query(info).get(args['id'])


list_voters_query = graphene.List(
    Voter,
    resolver=resolve_voters_by_fields)

get_voter_query = graphene.Field(
    Voter,
    resolver=resolve_voter_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


# TODO: Search for voter objects and elections from person identifiers?


#
# Mutations
#


class UpdateVoterPollBook(graphene.Mutation):
    """
    ???
    Add a pre-existing voter to another pollbook?
    Is this even possible?
    """
    class Arguments:
        id = graphene.UUID(required=True)
        pollbook_id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        # TODO:
        #   What even is this mutation?
        voter = evalg.models.voter.Voter.query.get(kwargs.get('id'))
        voter.pollbook_id = kwargs.get('pollbook_id')
        db.session.add(voter)
        db.session.commit()
        return UpdateVoterPollBook(ok=True)


class DeleteVotersInPollBook(graphene.Mutation):
    """
    Delete *all* voters in a given pollbook.
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        pollbook = evalg.models.pollbook.PollBook.query.get(kwargs.get('id'))
        for voter in pollbook.voters:
            db.session.delete(voter)
        db.session.commit()
        return DeleteVotersInPollBook(ok=True)


class AddVoter(graphene.Mutation):
    """
    Create a single voter object in a pollbook.
    """
    class Arguments:
        person_id = graphene.UUID(required=True)
        pollbook_id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        # TODO:
        #   We have to make sure that the person only has one active voter
        #   object in pollbooks for a given election.
        voter = evalg.models.voter.Voter()
        voter.person_id = kwargs.get('person_id')
        voter.pollbook_id = kwargs.get('pollbook_id')
        voter.voter_status = evalg.models.voter.VoterStatus.query.get('added')
        db.session.add(voter)
        db.session.commit()
        return AddVoter(ok=True)


class DeleteVoter(graphene.Mutation):
    """
    Delete a single voter object from a pollbook.
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        # TODO:
        #   Should we actually delete the object, or simply mark as deleted?
        #   If the object was added by an election admin from an import,
        #   shouldn't the voter entry stay there?
        voter = evalg.models.voter.Voter.query.get(kwargs.get('id'))
        db.session.delete(voter)
        db.session.commit()
        return DeleteVoter(ok=True)
