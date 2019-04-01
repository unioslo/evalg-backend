"""
GraphQL ObjectTypes for votes and vote mutations.
"""
import graphene
import graphene_sqlalchemy

import evalg.proc.vote
import evalg.database.query
import evalg.models.pollbook
import evalg.models.voter
import evalg.models.election


def get_session(info):
    return info.context.get('session')


#
# Query
#

class Vote(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.votes.Vote


def resolve_votes_by_person_id(_, info, **args):
    person_id = args['id']
    session = get_session(info)
    person = evalg.database.query.lookup(
        session,
        evalg.models.person.Person,
        id=person_id)
    return evalg.proc.vote.get_votes_for_person(session, person).all()


find_votes_query = graphene.List(
    Vote,
    resolver=resolve_votes_by_person_id,
    id=graphene.Argument(graphene.UUID, required=True))


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
    session = get_session(info)
    elec_id = args['id']
    election = evalg.database.query.lookup(
        session,
        evalg.models.election.Election,
        id=elec_id)
    data = {
        'id': elec_id,
    }
    data.update(evalg.proc.vote.get_election_vote_counts(session, election))
    return ElectionVoteCounts(**data)


#
# Mutations
#

# TODO:
#   Or should voting be a two step process?
#   1. Store ballot and get a ballot_id
#   2. Commit vote (e.g. create and store a Vote that binds a voter_id to the
#      ballot_id)

# TODO:
#   Should we have a more structured BallotInputObject to validate the ballot
#   content?

class AddVote(graphene.Mutation):
    class Arguments:
        voter_id = graphene.UUID(required=True)
        ballot = graphene.JSONString(required=True)

    ballot_id = graphene.UUID()
    election_id = graphene.UUID()
    ok = graphene.Boolean()

    def mutate(self, info, **args):
        voter_id = args['voter_id']
        ballot_data = args['ballot']
        session = get_session(info)
        voter = evalg.database.query.lookup(session,
                                            evalg.models.voter.Voter,
                                            id=voter_id)
        vote_policy = evalg.proc.vote.ElectionVotePolicy(session)
        vote = vote_policy.add_vote(voter, ballot_data)
        session.flush()

        node = AddVote(
            ballot_id=vote.ballot_id,
            election_id=voter.pollbook.election.id,
            ok=True)
        session.commit()
        return node
