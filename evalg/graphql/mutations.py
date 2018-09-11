import graphene
from flask import current_app
from graphene.types.generic import GenericScalar

from evalg import db
from evalg.metadata import make_group_from_template
from evalg.models.ou import OrganizationalUnit
from evalg.models.election import (Election as ElectionModel,
                                   ElectionGroup as ElectionGroupModel)
from evalg.models.authorization import (PersonPrincipal,
                                        GroupPrincipal,
                                        ElectionGroupRole)
from evalg.models.candidate import (Candidate as CandidateModel)
from evalg.metadata import (announce_group,
                            unannounce_group,
                            publish_group,
                            unpublish_group)
from evalg.graphql.entities import (Election,
                                    ElectionGroup,
                                    ElectionList,
                                    Candidate,
                                    Person,
                                    PollBook,
                                    Voter)


class CreateNewElectionGroup(graphene.Mutation):
    class Arguments:
        ou_id = graphene.UUID()
        template = graphene.Boolean()
        template_name = graphene.String()

    ok = graphene.Boolean()
    election_group = graphene.Field(lambda: ElectionGroup)

    def mutate(self, info, ou_id, template, template_name):
        ou = OrganizationalUnit.query.get(ou_id)
        election_group = make_group_from_template(template_name, ou)
        ok = True
        return CreateNewElectionGroup(election_group=election_group, ok=ok)


class ElectionBaseSettingsInput(graphene.InputObjectType):
    id = graphene.UUID(required=True)
    seats = graphene.Int(required=True)
    substitutes = graphene.Int(required=True)
    active = graphene.Boolean(required=True)


class UpdateBaseSettings(graphene.Mutation):
    class Input:
        elections = graphene.List(ElectionBaseSettingsInput, required=True)
        id = graphene.UUID(required=True)
        has_gender_quota = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        el_grp.meta['candidate_rules']['candidate_gender'] =\
            args.get('has_gender_quota')
        db.session.add(el_grp)
        for e in args.get('elections'):
            election = ElectionModel.query.get(e['id'])
            election.meta['candidate_rules']['seats'] = e.seats
            election.meta['candidate_rules']['substitutes'] = e.substitutes
            election.active = e.active
            db.session.add(election)
        db.session.commit()
        return UpdateBaseSettings(ok=True)


class ElectionVotingPeriodInput(graphene.InputObjectType):
    id = graphene.UUID(required=True)
    start = graphene.DateTime(required=True)
    end = graphene.DateTime(required=True)


class UpdateVotingPeriods(graphene.Mutation):
    class Input:
        elections = graphene.List(ElectionVotingPeriodInput, required=True)
        has_multiple_times = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        elections = args.get('elections')
        if not args.get('has_multiple_times'):
            for e in elections:
                election = ElectionModel.query.get(e['id'])
                election.start = elections[0].start
                election.end = elections[0].end
                db.session.add(election)
        else:
            for e in elections:
                election = ElectionModel.query.get(e['id'])
                election.start = e.start
                election.end = e.end
                db.session.add(election)
        db.session.commit()
        return UpdateVotingPeriods(ok=True)


class ElectionVoterInfoInput(graphene.InputObjectType):
    id = graphene.UUID(required=True)
    mandate_period_start = graphene.DateTime(required=True)
    mandate_period_end = graphene.DateTime(required=True)
    contact = graphene.String()
    information_url = graphene.String()


class UpdateVoterInfo(graphene.Mutation):
    class Input:
        elections = graphene.List(ElectionVoterInfoInput, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        elections = args.get('elections')
        for e in elections:
            election = ElectionModel.query.get(e['id'])
            election.mandate_period_start = e.mandate_period_start
            election.mandate_period_end = e.mandate_period_end
            election.contact = e.contact
            election.information_url = e.information_url
            db.session.add(election)

        db.session.commit()
        return UpdateVoterInfo(ok=True)


class AddAdmin(graphene.Mutation):
    class Input:
        admin_id = graphene.UUID(required=True)
        el_grp_id = graphene.UUID(required=True)
        type = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        if args.get('type') == 'person':
            principal = PersonPrincipal(person_id=args.get('admin_id'))
        else:
            principal = GroupPrincipal(group_id=args.get('admin_id'))
        role = ElectionGroupRole(role='election-admin',
                                 principal=principal,
                                 group_id=args.get('el_grp_id'))
        db.session.add(role)
        db.session.commit()
        return AddAdmin(ok=True)


class RemoveAdmin(graphene.Mutation):
    class Input:
        grant_id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        role = ElectionGroupRole.query.get(args.get('grant_id'))
        db.session.delete(role)
        db.session.commit()
        return AddAdmin(ok=True)


class AddPrefElecCandidate(graphene.Mutation):
    class Input:
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        meta = {'gender': args.get('gender')}
        candidate = CandidateModel(name=args.get('name'),
                                   meta=meta,
                                   list_id=args.get('list_id'),
                                   information_url=args.get('information_url'))
        db.session.add(candidate)
        db.session.commit()
        return AddPrefElecCandidate(ok=True)


class UpdatePrefElecCandidate(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        candidate = CandidateModel.query.get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['gender'] = args.get('gender')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        db.session.add(candidate)
        db.session.commit()
        return UpdatePrefElecCandidate(ok=True)


class CoCandidatesInput(graphene.InputObjectType):
    name = graphene.String(required=True)


class AddTeamPrefElecCandidate(graphene.Mutation):
    class Input:
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        meta = {'co_candidates': args.get('co_candidates')}
        candidate = CandidateModel(name=args.get('name'),
                                   meta=meta,
                                   list_id=args.get('list_id'),
                                   information_url=args.get('information_url'))
        db.session.add(candidate)
        db.session.commit()
        return AddTeamPrefElecCandidate(ok=True)


class UpdateTeamPrefElecCandidate(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        candidate = CandidateModel.query.get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['co_candidates'] = args.get('co_candidates')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        db.session.add(candidate)
        db.session.commit()
        return UpdateTeamPrefElecCandidate(ok=True)


class DeleteCandidate(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        candidate = CandidateModel.query.get(args.get('id'))
        db.session.delete(candidate)
        db.session.commit()
        return DeleteCandidate(ok=True)


class PublishElectionGroup(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        publish_group(el_grp)
        return PublishElectionGroup(ok=True)


class UnpublishElectionGroup(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        unpublish_group(el_grp)
        return UnpublishElectionGroup(ok=True)


class AnnounceElectionGroup(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        announce_group(el_grp)
        return AnnounceElectionGroup(ok=True)


class UnannounceElectionGroup(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        unannounce_group(el_grp)
        return UnannounceElectionGroup(ok=True)


class CreateElectionGroupKey(graphene.Mutation):
    class Input:
        id = graphene.UUID(required=True)
        key = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        el_grp = ElectionGroupModel.query.get(args.get('id'))
        el_grp.public_key = args.get('key')
        db.session.add(el_grp)
        db.session.commit()
        return CreateElectionGroupKey(ok=True)


class Mutations(graphene.ObjectType):
    create_new_election_group = CreateNewElectionGroup.Field()
    update_base_settings = UpdateBaseSettings.Field()
    update_voting_periods = UpdateVotingPeriods.Field()
    update_voter_info = UpdateVoterInfo.Field()
    add_admin = AddAdmin.Field()
    remove_admin = RemoveAdmin.Field()
    update_pref_elec_candidate = UpdatePrefElecCandidate.Field()
    add_pref_elec_candidate = AddPrefElecCandidate.Field()
    update_team_pref_elec_candidate = UpdateTeamPrefElecCandidate.Field()
    add_team_pref_elec_candidate = AddTeamPrefElecCandidate.Field()
    delete_candidate = DeleteCandidate.Field()
    publish_election_group = PublishElectionGroup.Field()
    unpublish_election_group = UnpublishElectionGroup.Field()
    announce_election_group = AnnounceElectionGroup.Field()
    unannounce_election_group = UnannounceElectionGroup.Field()
    create_election_group_key = CreateElectionGroupKey.Field()


