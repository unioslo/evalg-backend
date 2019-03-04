"""
GraphQL ObjectType for PollBook and Voter nodes.
"""
import graphene
import graphene_sqlalchemy

import evalg.database.query
import evalg.models.election
import evalg.models.person
import evalg.models.pollbook
import evalg.models.voter
import evalg.proc.pollbook
from evalg import db


def get_session(info):
    return info.context.get('session')

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


def resolve_voters_by_person_id(_, info, **args):
    person_id = args['id']
    session = get_session(info)
    person = evalg.database.query.lookup(
        session,
        evalg.models.person.Person,
        id=person_id)
    return evalg.proc.pollbook.get_voters_for_person(session, person).all()


list_voters_query = graphene.List(
    Voter,
    resolver=resolve_voters_by_fields)

get_voter_query = graphene.Field(
    Voter,
    resolver=resolve_voter_by_id,
    id=graphene.Argument(graphene.UUID, required=True))

# TODO: Re-design person-voter relationship
find_voters_query = graphene.List(
    Voter,
    resolver=resolve_voters_by_person_id,
    id=graphene.Argument(graphene.UUID, required=True))


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


VoterIdType = graphene.Enum.from_enum(
    evalg.models.person.IdType,
    description=evalg.models.person.IdType.get_description)


class AddVoterByIdentifier(graphene.Mutation):
    """
    Create a single voter object in a pollbook.
    """
    class Arguments:
        id_type = VoterIdType(required=True)
        id_value = graphene.String(required=True)
        pollbook_id = graphene.UUID(required=True)
        approved = graphene.Boolean(
            description='add a pre-approved voter to the poll book',
        )
        reason = graphene.String(
            description='reason for adding voter to the poll book',
        )

    Output = Voter

    def mutate(self, info, **kwargs):
        # TODO:
        #   We have to make sure that the person only has one active voter
        #   object in pollbooks for a given election.
        session = get_session(info)
        policy = evalg.proc.pollbook.ElectionVoterPolicy(session)
        id_type = kwargs['id_type']
        id_value = kwargs['id_value']
        pollbook_id = kwargs['pollbook_id']
        manual = not kwargs.get('approved', False)
        reason = kwargs.get('reason')

        pollbook = evalg.database.query.lookup(
            session,
            evalg.models.pollbook.PollBook,
            id=pollbook_id)

        voter = policy.add_voter_id(
            pollbook,
            id_type,
            id_value,
            manual=manual,
            reason=reason)

        db.session.commit()
        return voter


class AddVoterByPersonId(graphene.Mutation):
    """
    Create a single voter object in a pollbook.
    """
    class Arguments:
        person_id = graphene.UUID(required=True)
        pollbook_id = graphene.UUID(required=True)
        approved = graphene.Boolean(
            description='add a pre-approved voter to the poll book',
        )
        reason = graphene.String(
            description='reason for adding voter to the poll book',
        )

    Output = Voter

    def mutate(self, info, **kwargs):
        # TODO:
        #   We have to make sure that the person only has one active voter
        #   object in pollbooks for a given election.
        session = get_session(info)
        policy = evalg.proc.pollbook.ElectionVoterPolicy(session)
        person_id = kwargs['person_id']
        pollbook_id = kwargs['pollbook_id']
        manual = not kwargs.get('approved', False)
        reason = kwargs.get('reason')

        person = evalg.database.query.lookup(
            session,
            evalg.models.person.Person,
            id=person_id)

        pollbook = evalg.database.query.lookup(
            session,
            evalg.models.pollbook.PollBook,
            id=pollbook_id)

        voter = policy.add_voter(
            pollbook,
            person,
            manual=manual,
            reason=reason)

        db.session.commit()
        return voter


#
# TODO: Do we ever want to delete a voter? What do we do about any votes?
#
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
