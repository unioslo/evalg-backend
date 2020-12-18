"""GraphQL ObjectTypes for candidates and candidate lists."""
import logging

import graphene
import graphene_sqlalchemy

import evalg.models.candidate
import evalg.models.election_list
from evalg.graphql.nodes.utils.permissions import (
    permission_controller,
    permission_controlled_default_resolver,
    can_manage_election,
    can_manage_election_list,
)
from evalg.graphql.nodes.utils.base import get_current_user, get_session
from evalg.proc.candidate import (
    add_candidate,
    delete_candidate,
    update_candidate,
)
from evalg.proc.election_list import (
    add_election_list,
    delete_election_list,
    update_election_list,
)
from evalg.utils import convert_json

logger = logging.getLogger(__name__)

#
# Query
#


@permission_controller.control_object_type
class ElectionList(graphene_sqlalchemy.SQLAlchemyObjectType):
    """A list of candidates in a given election."""

    class Meta:
        model = evalg.models.election_list.ElectionList
        default_resolver = permission_controlled_default_resolver


@permission_controller.control_object_type
class Candidate(graphene_sqlalchemy.SQLAlchemyObjectType):
    """A candidate that may appear in a given election."""

    class Meta:
        model = evalg.models.candidate.Candidate
        default_resolver = permission_controlled_default_resolver

    @permission_controller
    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)


#
# Mutations
#

class LangDict(graphene.InputObjectType):
    """Tuple of name and language"""

    nb = graphene.String(required=True)
    nn = graphene.String(required=True)
    en = graphene.String(required=True)


class AddElectionList(graphene.Mutation):
    """Add a new election list to an election."""

    class Arguments:
        name = LangDict(required=True)
        election_id = graphene.UUID(required=True)
        description = LangDict()
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        election = session.query(
            evalg.models.election.Election).get(kwargs['election_id'])
        if not can_manage_election(session, user, election, **kwargs):
            return AddElectionList(ok=False)

        result = add_election_list(
            session=session,
            name=convert_json(kwargs.get('name')),
            election_id=kwargs.get('election_id'),
            description=convert_json(kwargs.get('description')),
            information_url=kwargs.get('information_url'))
        return AddElectionList(ok=result)


class UpdateElectionList(graphene.Mutation):
    """Update a pref election candidate."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = LangDict(required=True)
        election_id = graphene.UUID(required=True)
        description = LangDict()
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        election = session.query(
            evalg.models.election.Election).get(kwargs['election_id'])
        if not can_manage_election(session, user, election, **kwargs):
            return UpdateElectionList(ok=False)

        result = update_election_list(
            session=session,
            name=convert_json(kwargs.get('name')),
            election_list_id=kwargs.get('id'),
            election_id=kwargs.get('election_id'),
            description=convert_json(kwargs.get('description')),
            information_url=kwargs.get('information_url')
        )
        return UpdateElectionList(ok=result)


class DeleteElectionList(graphene.Mutation):
    """Delete a single election by id."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        e_list = session.query(
            evalg.models.election_list.ElectionList).get(kwargs.get('id'))
        if not can_manage_election(session, user, e_list.election, **kwargs):
            return DeleteElectionList(ok=False)
        result = delete_election_list(session, e_list.id)
        return DeleteElectionList(ok=result)


class AddPrefElecCandidate(graphene.Mutation):
    """Add a pref election candidate."""

    class Arguments:
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return AddPrefElecCandidate(ok=False)

        meta = {'gender': kwargs.get('gender')}
        result = add_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url'))
        return AddPrefElecCandidate(ok=result)


class UpdatePrefElecCandidate(graphene.Mutation):
    """Update a pref election candidate."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return UpdatePrefElecCandidate(ok=False)

        meta = {'gender': kwargs.get('gender')}
        result = update_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            candidate_id=kwargs.get('id'),
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url')
        )
        return UpdatePrefElecCandidate(ok=result)


class CoCandidatesInput(graphene.InputObjectType):
    """Co candidate graphql type."""

    name = graphene.String(required=True)


class AddTeamPrefElecCandidate(graphene.Mutation):
    """Add a team pref election candidate."""

    class Arguments:
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return AddTeamPrefElecCandidate(ok=False)

        meta = {'co_candidates': kwargs.get('co_candidates')}
        result = add_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url'))
        return AddTeamPrefElecCandidate(ok=result)


class UpdateTeamPrefElecCandidate(graphene.Mutation):
    """Update a team pref election candidate."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return UpdateTeamPrefElecCandidate(ok=False)

        meta = {'co_candidates': kwargs.get('co_candidates')}
        result = update_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            candidate_id=kwargs.get('id'),
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url'))
        return UpdateTeamPrefElecCandidate(ok=result)


class DeleteCandidate(graphene.Mutation):
    """Delete a single candidate by id."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        candidate = session.query(evalg.models.candidate.Candidate).get(
            kwargs.get('id'))
        kwargs['list_id'] = candidate.list_id
        if not can_manage_election_list(session, user, **kwargs):
            return DeleteCandidate(ok=False)
        result = delete_candidate(session, candidate.id)
        return DeleteCandidate(ok=result)


class AddListElecCandidate(graphene.Mutation):
    """Add a list election candidate."""

    class Arguments:
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        priority = graphene.Int(required=True)
        pre_cumulated = graphene.Boolean(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return AddPrefElecCandidate(ok=False)

        meta = {'gender': kwargs.get('gender')}
        result = add_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url'),
            priority=kwargs.get('priority'),
            pre_cumulated=kwargs.get('pre_cumulated')
        )
        return AddPrefElecCandidate(ok=result)


class UpdateListElecCandidate(graphene.Mutation):
    """Update a list election candidate."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        priority = graphene.Int(required=True)
        pre_cumulated = graphene.Boolean(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **kwargs):
            return UpdatePrefElecCandidate(ok=False)

        meta = {'gender': kwargs.get('gender')}
        result = update_candidate(
            session=session,
            name=kwargs.get('name'),
            meta=meta,
            candidate_id=kwargs.get('id'),
            election_list_id=kwargs.get('list_id'),
            information_url=kwargs.get('information_url'),
            priority=kwargs.get('priority'),
            pre_cumulated=kwargs.get('pre_cumulated')
        )
        return UpdatePrefElecCandidate(ok=result)
