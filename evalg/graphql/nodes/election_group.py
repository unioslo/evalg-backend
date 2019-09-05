"""
The GraphQL ElectionGroup ObjectType.

This module defines the GraphQL ObjectType that represents election group, as
well as queries and mutations for this object.
"""
import graphene
from graphene.types.generic import GenericScalar

import graphene_sqlalchemy

from graphql import GraphQLError

from sqlalchemy.sql import or_

from sqlalchemy_continuum import version_class

import evalg.models.election
import evalg.models.election_group_count
import evalg.models.ou
import evalg.models.person
import evalg.proc.authz
import evalg.proc.election
import evalg.proc.vote
import evalg.proc.count
from evalg import db
from evalg.graphql.nodes.utils import permissions
from evalg.election_templates import election_template_builder
from evalg.graphql import types
from evalg.graphql.nodes.utils.base import (get_session,
                                            get_current_user,
                                            MutationResponse)
from evalg.graphql.nodes.pollbook import Voter
from evalg.graphql.nodes.person import Person
from evalg.graphql.nodes.election import ElectionResult
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
        default_resolver = permissions.permission_controlled_default_resolver

    @permissions.permission_control_field
    def resolve_meta(self, info):
        return convert_json(self.meta)

    announcement_blockers = graphene.List(graphene.String)
    publication_blockers = graphene.List(graphene.String)
    published = graphene.Boolean()
    announced = graphene.Boolean()
    latest_election_group_count = graphene.Field(lambda: ElectionGroupCount)
    persons_with_multiple_verified_voters = graphene.List(
        lambda: PersonWithVoters
    )

    @permissions.permission_control_field
    def resolve_announcement_blockers(self, info):
        return evalg.proc.election.get_group_announcement_blockers(self)

    @permissions.permission_control_field
    def resolve_publication_blockers(self, info):
        return evalg.proc.election.get_group_publication_blockers(self)

    @permissions.permission_control_field
    def resolve_latest_election_group_count(self, info):
        session = get_session(info)
        group_id = self.id
        return evalg.proc.election.get_latest_election_group_count(
            session, group_id)

    @permissions.permission_control_field
    def resolve_persons_with_multiple_verified_voters(self, info):
        return resolve_persons_with_multiple_verified_voters(
            self,
            info,
            id=self.id
        )

    @classmethod
    def get_current_user_admin_roles(cls, info):
        session = get_session(info)
        current_user = get_current_user(info)
        return evalg.proc.authz.get_person_roles_matching(
            session=session,
            person=current_user.person,
            target_type='election-group-role',
            name='admin')

    @classmethod
    def get_query_visible_to_current_user(cls, info):
        admin_roles = cls.get_current_user_admin_roles(info)
        admin_for = [role.group_id for role in admin_roles]
        return cls.get_query(info).filter(
            or_(
                evalg.models.election.ElectionGroup.announced,
                evalg.models.election.ElectionGroup.published,
                evalg.models.election.ElectionGroup.id.in_(admin_for)
            )
        )


def resolve_election_groups(_, info):
    """
    List all election groups that should be visible to the current user.
    """
    return ElectionGroup.get_query_visible_to_current_user(info).all()


def resolve_election_group_by_id(_, info, **args):
    """
    Get a single election group that should be visible to the current user.
    """
    admin_roles = ElectionGroup.get_current_user_admin_roles(info)
    admin_for = [role.group_id for role in admin_roles]
    election_group = ElectionGroup.get_query(info).get(args['id'])
    if not election_group:
        return None
    if (
            args['id'] in admin_for or
            election_group.announced or
            election_group.published
    ):
        return election_group
    return None


list_election_groups_query = graphene.List(
    ElectionGroup,
    resolver=resolve_election_groups)


get_election_group_query = graphene.Field(
    ElectionGroup,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_group_by_id)


class PersonWithVoters(graphene.ObjectType):
    person = graphene.Field(Person)
    voters = graphene.List(Voter)


def resolve_persons_with_multiple_verified_voters(_, info, **args):
    election_group_id = args.get('id')
    session = get_session(info)
    user = get_current_user(info)
    el_grp = session.query(evalg.models.election.ElectionGroup).get(
        election_group_id)
    if not permissions.can_manage_election_group(session, user, el_grp):
        return None
    query = evalg.proc.vote.get_persons_with_multiple_verified_voters(
        session,
        election_group_id
    )

    class PersonWithVoters:
        def __init__(self, person, voter):
            self.person = person
            self.voters = [voter]

    person_id2person_with_voters = {}
    for person, voter in query.all():
        if person.id in person_id2person_with_voters.keys():
            person_id2person_with_voters[person.id].voters.append(voter)
        else:
            person_id2person_with_voters[person.id] = PersonWithVoters(
                person,
                voter
            )
    return person_id2person_with_voters.values()


persons_with_multiple_verified_voters_query = graphene.List(
    PersonWithVoters,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_persons_with_multiple_verified_voters
)


# TODO:
#   Election templates should *probably* have more structured output.


def resolve_election_template(_, info, **args):
    template = election_template_builder()
    return convert_json(template)


get_election_template_query = graphene.Field(
    GenericScalar,
    resolver=resolve_election_template)


class ElectionKeyMeta(graphene.ObjectType):
    """
    Election key meta info.
    """
    generated_at = types.DateTime()
    generated_by = graphene.Field(Person)


def resolve_election_key_meta(_, info, **args):
    election_group_id = args['id']
    session = get_session(info)
    user = get_current_user(info)
    el_grp = session.query(evalg.models.election.ElectionGroup).get(
        election_group_id)
    if not permissions.can_manage_election_group(session, user, el_grp):
        return None

    ElectionGroupVersion = version_class(evalg.models.election.ElectionGroup)

    key_meta = session.query(ElectionGroupVersion).filter(
        ElectionGroupVersion.id == election_group_id,
        ElectionGroupVersion.public_key_mod).order_by(
        ElectionGroupVersion.transaction_id.desc()).limit(1).all()

    if key_meta and len(key_meta) > 0:
        generated_at = key_meta[0].transaction.issued_at
        generated_by = key_meta[0].transaction.user

        return ElectionKeyMeta(
            generated_at=generated_at,
            generated_by=generated_by
        )
    raise GraphQLError('No info on key found')


get_election_key_meta_query = graphene.Field(
    ElectionKeyMeta,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_key_meta)


class ElectionGroupCount(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election_group_count.ElectionGroupCount
        default_resolver = permissions.permission_controlled_default_resolver

    election_results = graphene.List(ElectionResult)
    initiated_by = graphene.Field(Person)

    @permissions.permission_control_field
    def resolve_initiated_by(self, info):
        election_group_count_id = self.id
        ElectionGroupCountVersion = version_class(
            evalg.models.election_group_count.ElectionGroupCount)

        electionGroupCountChanges = db.session.query(
            ElectionGroupCountVersion
        ).filter(
            ElectionGroupCountVersion.id == election_group_count_id,
        ).order_by(
            ElectionGroupCountVersion.transaction_id).limit(1).all()

        if electionGroupCountChanges and len(electionGroupCountChanges) > 0:
            initiated_by = electionGroupCountChanges[0].transaction.user
            return initiated_by

        raise GraphQLError(
            'Could not resolve initiated_by - change record not found')


def resolve_election_group_count_by_id(_, info, **args):
    return ElectionGroupCount.get_query(info).get(args['id'])


get_election_group_count_query = graphene.Field(
    ElectionGroupCount,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_group_count_by_id)


def resolve_election_group_counting_results(_, info, **args):
    query = ElectionGroupCount.get_query(info)

    return query.filter(
        evalg.models.election_group_count.ElectionGroupCount.group_id ==
        args['id'])


list_election_group_counting_results_query = graphene.List(
    ElectionGroupCount,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_group_counting_results
)


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
        session = get_session(info)
        ou = session.query(evalg.models.ou.OrganizationalUnit).get(ou_id)
        election_group = evalg.proc.election.make_group_from_template(
            session, template_name, ou)
        current_user = get_current_user(info)
        current_user_principal = evalg.proc.authz.get_or_create_principal(
            session,
            principal_type='person',
            person_id=current_user.person.id)
        evalg.proc.authz.add_election_group_role(
            session=session,
            election_group=election_group,
            principal=current_user_principal,
            role_name='admin')
        session.commit()
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
        session = get_session(info)
        user = get_current_user(info)
        group_id = args.get('id')
        el_grp = evalg.models.election.ElectionGroup.query.get(group_id)
        if not permissions.can_manage_election_group(session, user, el_grp):
            return UpdateBaseSettings(ok=False)
        el_grp.meta['candidate_rules']['candidate_gender'] = args.get(
            'has_gender_quota')
        session.add(el_grp)
        for e in args.get('elections'):
            election = evalg.models.election.Election.query.get(e['id'])
            election.meta['candidate_rules']['seats'] = e.seats
            election.meta['candidate_rules']['substitutes'] = e.substitutes
            election.active = e.active
            session.add(election)
        session.commit()
        return UpdateBaseSettings(ok=True)


class PublishElectionGroup(graphene.Mutation):
    """
    Publish an ElectionGroup.
    """

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        election_group = evalg.models.election.ElectionGroup.query.get(
            args.get('id'))

        for election in election_group.elections:
            if not election.meta['counting_rules']['method']:
                evalg.proc.election.set_counting_method(session, election)

        evalg.proc.election.publish_group(session, election_group)
        return PublishElectionGroup(ok=True)


class UnpublishElectionGroup(graphene.Mutation):
    """
    Unpublish an ElectionGroup.
    """

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        election_group = evalg.models.election.ElectionGroup.query.get(
            args.get('id'))
        evalg.proc.election.unpublish_group(session, election_group)
        return UnpublishElectionGroup(ok=True)


class AnnounceElectionGroup(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        election_group = evalg.models.election.ElectionGroup.query.get(
            args.get('id'))
        evalg.proc.election.announce_group(session, election_group)
        return AnnounceElectionGroup(ok=True)


class UnannounceElectionGroup(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        election_group = evalg.models.election.ElectionGroup.query.get(
            args.get('id'))
        evalg.proc.election.unannounce_group(session, election_group)
        return UnannounceElectionGroup(ok=True)


class SetElectionGroupKeyResponse(MutationResponse):
    pass


class SetElectionGroupKey(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        public_key = graphene.String(required=True)

    Output = SetElectionGroupKeyResponse

    def mutate(self, info, **args):
        group_id = args['id']
        public_key = args['public_key']
        session = get_session(info)
        user = get_current_user(info)
        group = session.query(evalg.models.election.ElectionGroup).get(
            group_id)
        if not permissions.can_manage_election_group(session, user, group):
            return SetElectionGroupKeyResponse(
                success=False,
                code='permission-denied',
                message='Not allowed to set election group key for election '
                        'group {}'.format(group_id)
            )
        for election in group.elections:
            if group.public_key and group.published:
                return SetElectionGroupKeyResponse(
                    success=False,
                    code='cannot-change-key-if-published',
                    message=('The public key cannot be changed if '
                             'an election is published'))
            elif group.public_key and election.active and election.has_started:
                return SetElectionGroupKeyResponse(
                    success=False,
                    code='cannot-change-key-if-past-start',
                    message=('The public key cannot be changed if '
                             'an election has started'))
            else:
                count = evalg.proc.vote.get_election_vote_counts(
                    session, election)
                if any(count.values()):
                    return SetElectionGroupKeyResponse(
                        success=False,
                        code='cannot-change-key-if-votes-exist',
                        message=('The public key cannot be changed if '
                                 'a vote has been cast'))
        group.public_key = public_key
        session.add(group)
        session.commit()
        return SetElectionGroupKeyResponse(success=True)


class CountElectionGroupResponse(MutationResponse):
    election_group_count_id = graphene.UUID()


class CountElectionGroup(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        election_key = graphene.String(required=True)

    Output = CountElectionGroupResponse

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        group_id = args['id']
        election_key = args['election_key']

        election_group_counter = evalg.proc.count.ElectionGroupCounter(
            session,
            group_id,
            election_key
        )

        if not permissions.can_manage_election_group(
                session, user, election_group_counter.group):
            return CountElectionGroupResponse(
                success=False,
                code='permission-denied',
                message='Not allowed to count election group {}'.format(
                    group_id)
            )
        if evalg.proc.vote.get_persons_with_multiple_verified_voters(
                session,
                group_id
        ).all():
            return CountElectionGroupResponse(
                success=False,
                code='persons-with-multiple-votes',
                message='There are person(s) who have multiple verified votes'
            )

        if evalg.proc.vote.get_voters_in_election_group(
                session,
                group_id,
                self_added=True,
                reviewed=False
        ).all():
            return CountElectionGroupResponse(
                success=False,
                code='unreviewed-self-added-voters',
                message='All self added voters must be reviewed'
            )

        if not election_group_counter.ballot_serializer:
            return CountElectionGroupResponse(
                success=False,
                code='invalid-election-key-wrong-format',
                message='The given election key is invalid')

        if not election_group_counter.verify_election_key():
            return CountElectionGroupResponse(
                success=False,
                code='invalid-election-key',
                message='The given election key is invalid')

        if not election_group_counter.group.status == 'closed':
            return CountElectionGroupResponse(
                success=False,
                code='cannot-count-before-all-elections-are-closed',
                message='All of the elections in an election group must be'
                        ' closed to count votes')

        # Creating an election_group_count entry in the db
        count = election_group_counter.log_start_count()
        election_group_counter.deserialize_ballots()
        election_group_counter.process_for_count()

        if info.context['user'].person:
            election_group_counter.generate_results(
                count,
                getattr(info.context['user'].person, 'display_name', None))
        else:
            election_group_counter.generate_results(count)

        count = election_group_counter.log_finalize_count(count)

        return CountElectionGroupResponse(success=True,
                                          election_group_count_id=count.id)
