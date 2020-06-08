"""GraphQL ObjectType for Pollbook and Voter nodes."""
import datetime
import logging

import graphene
import graphene_sqlalchemy
from graphene_file_upload.scalars import Upload
from graphene.types.generic import GenericScalar

from sentry_sdk import capture_exception

import evalg.database.query
import evalg.models.census_file_import
import evalg.models.election
import evalg.models.person
import evalg.models.pollbook
import evalg.models.voter
import evalg.proc.pollbook
from evalg.graphql.types import PersonIdType
from evalg.file_parser.parser import CensusFileParser
from evalg.graphql.nodes.utils.base import (get_session, get_current_user,
                                            MutationResponse)
from evalg.graphql.nodes.person import Person
from evalg.graphql.nodes.utils.permissions import (
    permission_controlled_default_resolver,
    permission_controller,
    can_vote,
    can_manage_pollbook,
    can_manage_voter,
)

logger = logging.getLogger(__name__)


#
# Query
#
@permission_controller.control_object_type
class Voter(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.voter.Voter
        default_resolver = permission_controlled_default_resolver

    verified_status = graphene.Enum.from_enum(
        evalg.models.voter.VerifiedStatus)()
    person = graphene.Field(Person)
    has_voted = graphene.Field(graphene.types.Boolean)

    @permission_controller
    def resolve_person(self, info):
        voter_id = self.id
        session = get_session(info)
        voter = session.query(evalg.models.voter.Voter).get(voter_id)
        return evalg.proc.pollbook.get_person_for_voter(session, voter)

    @permission_controller
    def resolve_has_voted(self, info):
        return len(self.votes) > 0


@permission_controller.control_object_type
class Pollbook(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.pollbook.Pollbook
        default_resolver = permission_controlled_default_resolver

    self_added_voters = graphene.List(lambda: Voter)
    admin_added_voters = graphene.List(lambda: Voter)
    verified_voters_count = graphene.Int()
    verified_voters_with_votes_count = graphene.Int()
    voters_with_vote = graphene.List(lambda: Voter)
    voters_without_vote = graphene.List(lambda: Voter)
    nr_of_voters = graphene.types.Int()
    voter_dump = graphene.Field(GenericScalar)

    @permission_controller
    def resolve_nr_of_voters(self, info):
        return len(self.voters)

    @permission_controller
    def resolve_self_added_voters(self, info):
        return self.self_added_voters

    @permission_controller
    def resolve_admin_added_voters(self, info):
        return self.voters_admin_added

    @permission_controller
    def resolve_verified_voters_count(self, info):
        return len(self.valid_voters)

    @permission_controller
    def resolve_verified_voters_with_votes_count(self, info):
        return len(self.valid_voters_with_vote)

    @permission_controller
    def resolve_voters_with_vote(self, info):
        return self.valid_voters_with_vote

    @permission_controller
    def resolve_voters_without_vote(self, info):
        return self.valid_voters_without_vote

    @permission_controller
    def resolve_voter_dump(self, info):
        return [[x.id_type, x.id_value, x.has_voted] for x in self.voters]


@permission_controller.control_object_type
class CensusFileImport(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.census_file_import.CensusFileImport
        # Binary blob not supported by graphql
        exclude_fields = ('census_file',)
        default_resolver = permission_controlled_default_resolver


def resolve_search_voters(_, info, **kwargs):
    election_group_id = kwargs.pop('election_group_id')
    session = get_session(info)

    if 'search' in kwargs and kwargs.get('search') == '':
        # Return nothing if the search string is empty
        return []

    if 'limit' in kwargs:
        limit = kwargs.pop('limit')
        return evalg.proc.pollbook.get_voters_in_election_group(
            session, election_group_id, **kwargs
        ).order_by('id').limit(limit).all()

    return evalg.proc.pollbook.get_voters_in_election_group(
        session, election_group_id, **kwargs
    ).all()


def resolve_voters_by_person_id(_, info, **kwargs):
    person_id = kwargs['id']
    session = get_session(info)
    person = session.query(evalg.models.person.Person).get(person_id)
    return evalg.proc.pollbook.get_voters_for_person(session, person).all()


search_voters_query = graphene.List(
    Voter,
    resolver=resolve_search_voters,
    election_group_id=graphene.Argument(graphene.UUID, required=True),
    self_added=graphene.Argument(graphene.Boolean, required=False),
    reviewed=graphene.Argument(graphene.Boolean, required=False),
    verified=graphene.Argument(graphene.Boolean, required=False),
    has_voted=graphene.Argument(graphene.Boolean, required=False),
    limit=graphene.Argument(graphene.Int, required=False),
    search=graphene.Argument(graphene.String, required=False),
    pollbook_id=graphene.Argument(graphene.UUID, required=False),
)


# TODO: Re-design person-voter relationship
find_voters_query = graphene.List(
    Voter,
    resolver=resolve_voters_by_person_id,
    id=graphene.Argument(graphene.UUID, required=True))


#
# Mutations
#

class UpdateVoterPollbook(graphene.Mutation):
    """
    Add a pre-existing voter to another pollbook.

    The pollbook needs to be in the same election group as the source.
    """

    class Arguments:
        id = graphene.UUID(required=True)
        pollbook_id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))

        if not can_manage_voter(session, user, voter):
            return UpdateVoterPollbook(ok=False)

        pollbook = session.query(evalg.models.pollbook.Pollbook).get(
            kwargs.get('pollbook_id'))

        if not can_manage_pollbook(session, user, pollbook):
            return UpdateVoterPollbook(ok=False)

        election_group_from = voter.pollbook.election.election_group.id
        election_group_to = pollbook.election.election_group.id

        if election_group_from != election_group_to:
            # Do not move voters between election_groups
            return UpdateVoterPollbook(ok=False)

        voter.pollbook_id = kwargs.get('pollbook_id')
        session.add(voter)
        session.commit()
        return UpdateVoterPollbook(ok=True)


class UpdateVoterReason(graphene.Mutation):
    """Update the voters reason for why they should be able to vote."""

    class Arguments:
        id = graphene.UUID(required=True)
        reason = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not can_vote(session, user, voter):
            return UpdateVoterReason(ok=False)
        voter.reason = kwargs.get('reason')
        # A new review is needed if the reason is updated
        voter.ensure_rereview()
        session.add(voter)
        session.commit()
        return UpdateVoterReason(ok=True)


class UndoReviewVoter(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not can_manage_voter(session, user, voter):
            return UndoReviewVoter(ok=False)

        voter.undo_review()
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
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not can_manage_voter(session, user, voter):
            return ReviewVoter(ok=False)
        voter.reviewed = True
        voter.verified = kwargs.get('verify')
        session.add(voter)
        session.commit()
        return ReviewVoter(ok=True)


class DeleteVotersInPollbook(graphene.Mutation):
    """Delete *all* voters in a given pollbook."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        pollbook = session.query(evalg.models.pollbook.Pollbook).get(
            kwargs.get('id'))
        if not can_manage_pollbook(session, user, pollbook):
            return DeleteVotersInPollbook(ok=False)
        for voter in pollbook.voters:
            if not voter.votes:
                session.delete(voter)
        session.commit()
        return DeleteVotersInPollbook(ok=True)


class AddVoterByIdentifier(graphene.Mutation):
    """Create a single voter object in a pollbook."""

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

        pollbook = session.query(evalg.models.pollbook.Pollbook).get(
            pollbook_id)

        if not can_manage_pollbook(session, user, pollbook):
            return None

        voter = policy.add_voter_id(
            pollbook,
            id_type,
            id_value,
            self_added=self_added,
            reason=reason)

        session.commit()
        return voter


class AddVoterByPersonId(graphene.Mutation):
    """
    Create a single voter object in a pollbook.

    Used by person when voting.
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
        user = get_current_user(info)
        policy = evalg.proc.pollbook.ElectionVoterPolicy(session)
        person_id = kwargs['person_id']
        pollbook_id = kwargs['pollbook_id']
        reason = kwargs.get('reason')

        person = session.query(evalg.models.person.Person).get(person_id)

        pollbook = session.query(evalg.models.pollbook.Pollbook).get(
            pollbook_id)

        if (not can_manage_pollbook(session, user, pollbook)
                and user.person.id != person_id):
            # Only allow users to add themselves to a pollbook they do not own
            return None

        voter = policy.add_voter(
            pollbook,
            person,
            self_added=True,
            reason=reason)

        session.commit()
        return voter


class DeleteVoter(graphene.Mutation):
    """Delete a single voter object from a pollbook."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        voter = session.query(evalg.models.voter.Voter).get(kwargs.get('id'))
        if not can_manage_pollbook(session, user, voter.pollbook):
            return DeleteVoter(ok=False)
        if voter.self_added:
            return DeleteVoter(ok=False)
        if voter.votes:
            return DeleteVoter(ok=False)

        session.delete(voter)
        session.commit()
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

        try:
            pollbook = session.query(evalg.models.pollbook.Pollbook).get(
                pollbook_id)
        except Exception as e:
            capture_exception(e)
            return UploadCensusFileResponse(
                success=False,
                code='pollbook-not-found',
                message='No pollbook with id {!r}'.format(pollbook_id))

        if not can_manage_pollbook(session, user, pollbook):
            return UploadCensusFileResponse(
                success=False,
                code='permission-denied',
                message='No access to pollbook id {!r}'.format(pollbook_id))

        logger.info('Updating %r from %r', pollbook, census_file)
        file_content = census_file.read()
        parser = CensusFileParser.factory(file_content,
                                          census_file.mimetype)
        if not parser:
            return UploadCensusFileResponse(
                success=False,
                code='unsupported-file-type',
                message='Unsupported file type {!r}'.format(
                    census_file.mimetype))

        file_import = evalg.models.census_file_import.CensusFileImport(
            initiated_at=datetime.datetime.now(datetime.timezone.utc),
            file_name=census_file.filename,
            census_file=file_content,
            mime_type=census_file.mimetype,
            pollbook_id=pollbook_id
        )

        session.add(file_import)
        session.commit()

        from evalg.tasks.celery_worker import import_census_file_task
        import_census_file_task.delay(pollbook_id, file_import.id)

        logger.info('Started file import as celery job')

        return UploadCensusFileResponse(success=True)
