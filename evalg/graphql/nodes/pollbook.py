"""GraphQL ObjectType for PollBook and Voter nodes."""
import collections
import logging

import graphene
import graphene_sqlalchemy
from graphene_file_upload.scalars import Upload

import evalg.database.query
import evalg.models.election
import evalg.models.person
import evalg.models.pollbook
import evalg.models.voter
import evalg.proc.pollbook
from evalg import db
from evalg.graphql.types import PersonIdType
from evalg.file_parser.parser import CensusFileParser
from evalg.models.voter import VerifiedStatus, VERIFIED_STATUS_MAP
from evalg.graphql.nodes.utils.base import (get_session, get_current_user,
                                            MutationResponse)
from evalg.graphql.nodes.person import Person
from evalg.graphql.nodes.utils import permissions


logger = logging.getLogger(__name__)

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


class Voter(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.voter.Voter
        default_resolver = permissions.permission_controlled_default_resolver

    verified_status = graphene.Enum.from_enum(
        evalg.models.voter.VerifiedStatus
    )()

    person = graphene.Field(Person)

    @permissions.permission_control_field
    def resolve_person(self, info):
        voter_id = self.id
        session = get_session(info)
        voter = evalg.database.query.lookup(
            session,
            evalg.models.voter.Voter,
            id=voter_id)
        return evalg.proc.vote.get_person_for_voter(session, voter)


class PollBook(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.pollbook.PollBook
        default_resolver = permissions.permission_controlled_default_resolver

    self_added_voters = graphene.List(lambda: Voter)
    admin_added_voters = graphene.List(lambda: Voter)
    verified_voters_count = graphene.Int()
    verified_voters_with_votes_count = graphene.Int()

    voters_with_vote = graphene.List(lambda: Voter)
    voters_without_vote = graphene.List(lambda: Voter)

    @permissions.permission_control_field
    def resolve_self_added_voters(self, info):
        session = get_session(info)
        return evalg.proc.vote.get_voters_by_self_added(session,
                                                        self.id,
                                                        self_added=True).all()

    @permissions.permission_control_field
    def resolve_admin_added_voters(self, info):
        session = get_session(info)
        return evalg.proc.vote.get_voters_by_self_added(session,
                                                        self.id,
                                                        self_added=False).all()

    @permissions.permission_control_field
    def resolve_verified_voters_count(self, info):
        session = get_session(info)
        return evalg.proc.vote.get_verified_voters_count(session, self.id)

    @permissions.permission_control_field
    def resolve_verified_voters_with_votes_count(self, info):
        session = get_session(info)
        return evalg.proc.vote.get_verified_voters_with_votes_count(
            session, self.id)

    @permissions.permission_control_field
    def resolve_voters_with_vote(self, info):
        session = get_session(info)
        return evalg.proc.pollbook.get_voters_with_vote_in_pollbook(
            session, self.id)

    @permissions.permission_control_field
    def resolve_voters_without_vote(self, info):
        session = get_session(info)
        return evalg.proc.pollbook.get_voters_without_vote_in_pollbook(
            session, self.id)


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


def resolve_voters_by_fields(_, info):
    return Voter.get_query(info).all()


def resolve_search_voters(_, info, **args):
    election_group_id = args.pop('election_group_id')
    session = get_session(info)
    return evalg.proc.vote.get_voters_in_election_group(
        session, election_group_id, **args
    ).all()


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


search_voters_query = graphene.List(
    Voter,
    resolver=resolve_search_voters,
    election_group_id=graphene.Argument(graphene.UUID, required=True),
    self_added=graphene.Argument(graphene.Boolean, required=False),
    reviewed=graphene.Argument(graphene.Boolean, required=False),
    verified=graphene.Argument(graphene.Boolean, required=False),
    has_voted=graphene.Argument(graphene.Boolean, required=False),
)


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
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not permissions.can_vote(session, user, voter):
            return UpdateVoterPollBook(ok=False)
        voter.pollbook_id = kwargs.get('pollbook_id')
        db.session.add(voter)
        db.session.commit()
        return UpdateVoterPollBook(ok=True)


class UpdateVoterReason(graphene.Mutation):
    """
    Update the voters supplied reason for why they
    should be able to vote in the election.
    """
    class Arguments:
        id = graphene.UUID(required=True)
        reason = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not permissions.can_vote(session, user, voter):
            return UpdateVoterReason(ok=False)
        voter.reason = kwargs.get('reason')
        session.add(voter)
        session.commit()
        return UpdateVoterReason(ok=True)


def undo_review_self_added_voter(voter):
    voter.reviewed = False
    voter.verified = False


def undo_review_admin_added_voter(voter):
    voter.reviewed = False
    voter.verified = True


class UndoReviewVoter(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not permissions.can_manage_voter(session, user, voter):
            return UndoReviewVoter(ok=False)
        verified_status = VERIFIED_STATUS_MAP.get(
            (voter.self_added, voter.reviewed, voter.verified),
            None
        )

        if verified_status in (VerifiedStatus.SELF_ADDED_VERIFIED,
                               VerifiedStatus.SELF_ADDED_REJECTED):
            undo_review_self_added_voter(voter)
        elif verified_status is VerifiedStatus.ADMIN_ADDED_REJECTED:
            undo_review_admin_added_voter(voter)
        else:
            return UndoReviewVoter(ok=False)

        session.add(voter)
        session.commit()
        return UndoReviewVoter(ok=True)


class ReviewVoter(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        verify = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not permissions.can_manage_voter(session, user, voter):
            return ReviewVoter(ok=False)
        voter.reviewed = True
        voter.verified = kwargs.get('verify')
        session.add(voter)
        session.commit()
        return ReviewVoter(ok=True)


class DeleteVotersInPollBook(graphene.Mutation):
    """
    Delete *all* voters in a given pollbook.
    """

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user
        pollbook = session.query(evalg.models.pollbook.PollBook).get(
            kwargs.get('id'))
        if not permissions.can_manage_pollbook(session, user, pollbook):
            return DeleteVotersInPollBook(ok=False)
        for voter in pollbook.voters:
            db.session.delete(voter)
        db.session.commit()
        return DeleteVotersInPollBook(ok=True)


class AddVoterByIdentifier(graphene.Mutation):
    """
    Create a single voter object in a pollbook. Only available to admin.
    """

    class Arguments:
        id_type = PersonIdType(required=True)
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
        session = get_session(info)
        user = get_current_user(info)
        policy = evalg.proc.pollbook.ElectionVoterPolicy(session)
        id_type = kwargs['id_type']
        id_value = kwargs['id_value']
        pollbook_id = kwargs['pollbook_id']
        self_added = not kwargs.get('approved', False)
        reason = kwargs.get('reason')

        pollbook = evalg.database.query.lookup(
            session,
            evalg.models.pollbook.PollBook,
            id=pollbook_id)

        if not permissions.can_manage_pollbook(session, user, pollbook):
            return None

        voter = policy.add_voter_id(
            pollbook,
            id_type,
            id_value,
            self_added=self_added,
            reason=reason)

        db.session.commit()
        return voter


class AddVoterByPersonId(graphene.Mutation):
    """
    Create a single voter object in a pollbook. Used by person when voting.
    """

    class Arguments:
        person_id = graphene.UUID(required=True)
        pollbook_id = graphene.UUID(required=True)
        reason = graphene.String(
            description='reason for adding voter to the poll book',
        )

    Output = Voter

    def mutate(self, info, **kwargs):
        session = get_session(info)
        policy = evalg.proc.pollbook.ElectionVoterPolicy(session)
        person_id = kwargs['person_id']
        pollbook_id = kwargs['pollbook_id']
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
            self_added=True,
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
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not permissions.can_manage_pollbook(session, user, voter.pollbook):
            return DeleteVoter(ok=False)
        db.session.delete(voter)
        db.session.commit()
        return DeleteVoter(ok=True)


class UploadCensusFileResponse(MutationResponse):
    num_failed = graphene.Int()
    num_ok = graphene.Int()


class UploadCensusFile(graphene.Mutation):
    """Upload and parse census file."""

    class Arguments:
        pollbook_id = graphene.UUID(required=True)
        census_file = Upload(required=True)

    Output = UploadCensusFileResponse

    def mutate(self, info, **kwargs):
        user = get_current_user(info)
        pollbook_id = kwargs['pollbook_id']
        census_file = kwargs['census_file']
        session = get_session(info)
        voters = evalg.proc.pollbook.ElectionVoterPolicy(session)
        result = collections.Counter(ok=0, failed=0)

        logger.debug('kwargs %r', kwargs)

        try:
            pollbook = evalg.database.query.lookup(
                evalg.db.session,
                evalg.models.pollbook.PollBook,
                id=pollbook_id)
        except Exception as e:
            return UploadCensusFileResponse(
                success=False,
                code='pollbook-not-found',
                message='No pollbook with id {!r}'.format(pollbook_id))

        if not permissions.can_manage_pollbook(session, user, pollbook):
            return UploadCensusFile(ok=False)

        logger.info('Updating %r from %r', pollbook, census_file)
        parser = CensusFileParser.factory(census_file)
        if not parser:
            return UploadCensusFileResponse(
                success=False,
                code='unsupported-file-type',
                message='Unsupported file type {!r}'.format(
                    census_file.mimetype))

        id_type = parser.id_type
        logger.debug('Loading file using parser %r (id_type=%r)',
                     type(parser), id_type)
        for i, id_value in enumerate(parser.parse(), 1):
            try:
                voters.add_voter_id(pollbook, id_type, id_value,
                                    self_added=False)
            except Exception as e:
                logger.warning('Entry #%d: unable to add voter: %s',
                               i, e, exc_info=True)
                result['failed'] += 1
                continue
            result['ok'] += 1

        session.commit()
        return UploadCensusFileResponse(
            success=True,
            num_failed=result['failed'],
            num_ok=result['ok'])
