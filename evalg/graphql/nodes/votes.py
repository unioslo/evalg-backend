"""
GraphQL ObjectTypes for votes and vote mutations.
"""
import graphene
import graphene_sqlalchemy

from flask import current_app

import evalg.database.query
import evalg.models.pollbook
import evalg.models.voter
import evalg.models.election
import evalg.proc.vote

from evalg.graphql.nodes.utils.base import get_session, get_current_user
from evalg.graphql.nodes.utils.permissions import (
    permission_controlled_default_resolver,
    permission_controller,
    can_manage_election,
    can_vote,
)

#
# Query
#
@permission_controller.control_object_type
class Vote(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.votes.Vote
        default_resolver = permission_controlled_default_resolver


class ElectionVoteCounts(graphene.ObjectType):
    """ Vote counts for election, grouped by voter status. """
    id = graphene.UUID()

    total = graphene.Int(
        default_value=0,
        description='total votes'
    )

    self_added_not_reviewed = graphene.Int(
        default_value=0,
        description='voters not in census, admin review needed'
    )

    admin_added_rejected = graphene.Int(
        default_value=0,
        description='voter in census, rejected by admin'
    )

    self_added_rejected = graphene.Int(
        default_value=0,
        description='voter not in census, rejected by admin'
    )

    admin_added_auto_verified = graphene.Int(
        default_value=0,
        description='voter in census'
    )

    self_added_verified = graphene.Int(
        default_value=0,
        description='voter not in census, verified by admin'
    )


def resolve_election_count_by_id(_, info, **args):
    user = get_current_user(info)
    session = get_session(info)
    elec_id = args['id']
    election = evalg.database.query.lookup(
        session,
        evalg.models.election.Election,
        id=elec_id)
    if not can_manage_election(session, user, election):
        return None
    data = {
        'id': elec_id,
    }
    data.update(evalg.proc.vote.get_election_vote_counts(session, election))
    return ElectionVoteCounts(**data)


#
# Mutations
#
class AddVote(graphene.Mutation):
    class Arguments:
        voter_id = graphene.UUID(required=True)
        ballot = graphene.JSONString(required=True)

    ballot_id = graphene.UUID()
    election_id = graphene.UUID()
    ok = graphene.Boolean()

    def mutate(self, info, **args):
        user = get_current_user(info)
        voter_id = args['voter_id']
        ballot_data = args['ballot']
        session = get_session(info)
        vote_policy = evalg.proc.vote.ElectionVotePolicy(session, voter_id)

        if not vote_policy.voter:
            return AddVote(ok=False)

        if not can_vote(session, user, vote_policy.voter):
            return AddVote(ok=False)

        if not vote_policy.verify_election_is_ongoing():
            return AddVote(ok=False)

        if not vote_policy.verify_ballot_content(ballot_data):
            return AddVote(ok=False)

        ballot_data.__delitem__('isBlankVote')
        ballot_data['pollbookId'] = str(vote_policy.voter.pollbook.id)
        vote = vote_policy.add_vote(ballot_data)
        session.flush()

        node = AddVote(
            ballot_id=vote.ballot_id,
            election_id=vote_policy.voter.pollbook.election.id,
            ok=True)
        session.commit()

        from evalg.tasks.celery_worker import send_vote_confirmation_mail_task

        election_group = vote_policy.voter.pollbook.election.election_group
        election_group_name = election_group.name

        if current_app.config.get('MAIL_ENABLE'):
            send_vote_confirmation_mail_task.delay(
                user.person.email,
                election_group_name)

        return node
