#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Functional API for handling election metadata."""
import datetime

import aniso8601
from flask import current_app
from functools import wraps
from .models.election import ElectionGroup, Election
from .models.pollbook import PollBook
from .models.election_list import ElectionList
from .api import NotFoundError, BadRequest
from .authorization import check_perms, all_perms, PermissionDenied
from evalg import db


def eperm(permission, arg=0):
    """Check perms function for election"""
    assert permission in all_perms, '{} not valid'.format(permission)
    if isinstance(arg, int):
        def election(args, kw):
            return args[arg]
    else:
        def election(args, kw):
            return kw[arg]

    def fun(f):
        @wraps(f)
        def gun(*args, **kw):
            if 'principals' in kw:
                principals = kw['principals']
                del kw['principals']
            else:
                principals = ()
            e = election(args, kw)
            if current_app.config['AUTH_ENABLED'] \
                    and not check_perms(principals,
                                        permission,
                                        election=e,
                                        ou=e.ou):
                raise PermissionDenied()
            return f(*args, **kw)

        gun.is_protected = True
        return gun
    return fun


def rperm(*permission):
    """Check if user has perms on return value. """
    for perm in permission:
        assert perm in all_perms

    def fun(f):
        @wraps(f)
        def gun(*args, **kw):
            if 'principals' in kw:
                principals = kw['principals']
                del kw['principals']
            else:
                principals = ()
            ret = f(*args, **kw)
            if ret is not None:
                if not check_perms(principals, permission, election=ret,
                                   ou=ret.ou):
                    raise PermissionDenied()
            return ret
        gun.is_protected = True
        return gun
    return fun


@rperm('view-election')
def get_group(group_id):
    """Look up election group."""
    group = ElectionGroup.query.get(group_id)
    if group is None:
        raise NotFoundError(
            details="No such election group with id={uuid}".format(
                uuid=group_id))
    return group


@rperm('view-election')
def get_election(election_id):
    """Look up election."""
    election = Election.query.get(election_id)
    if election is None:
        raise NotFoundError(
            details="No such election with id={uuid}".format(
                uuid=election_id))
    return election


def list_elections(group=None):
    """List all elections or elections in group."""
    if group is None:
        return Election.query.all()
    else:
        return group.elections


@eperm('change-election-metadata')
def update_election(election, **fields):
    """Update election fields"""
    for k, v in fields.items():
        if not hasattr(election, k):
            continue
        if getattr(election, k) != v:
            setattr(election, k, v)
    db.session.commit()
    return election


@eperm('announce-election')
def announce_group(group, **fields):
    """Announce an election group."""
    blockers = group_announcement_blockers(group)
    if blockers:
        raise BadRequest(details=blockers[0])
    group.announce()
    db.session.commit()
    return group


@eperm('announce-election')
def unannounce_group(group, **fields):
    """Unannounce an election group."""
    group.unannounce()
    db.session.commit()
    return group


def group_announcement_blockers(group):
    """Check whether an election group can be announced."""
    blockers = []
    if group.announced:
        blockers.append('already-announced')
    for election in group.elections:
        if election.active:
            if missing_start_or_end(election):
                blockers.append('missing-start-or-end')
            if start_after_end(election):
                blockers.append('start-must-be-before-end')
    return blockers


@eperm('publish-election')
def publish_group(group, **fields):
    """Publish an election group."""
    blockers = group_publication_blockers(group)
    if blockers:
        raise BadRequest(details=blockers[0])
    group.publish()
    db.session.commit()
    return group


@eperm('publish-election')
def unpublish_group(group, **fields):
    """Unpublish an election group."""
    group.unpublish()
    db.session.commit()
    return group


def group_publication_blockers(group):
    """Check whether an election group can be published."""
    blockers = []
    if group.published:
        blockers.append('already-published')
    if not group.public_key:
        blockers.append('missing-key')
    for election in group.elections:
        if election.active:
            if missing_start_or_end(election):
                blockers.append('missing-start-or-end')
            if start_after_end(election):
                blockers.append('start-must-be-before-end')
    return blockers


def missing_start_or_end(election):
    return not election.start or not election.end


def start_after_end(election):
    if missing_start_or_end(election):
        return False
    return election.start > election.end


@eperm('change-election-metadata')
def update_group(group, **fields):
    """Update group fields. """
    for k, v in fields.items():
        if not hasattr(group, k):
            continue
        if getattr(group, k) != v:
            setattr(group, k, v)
    db.session.commit()
    return group


@eperm('change-election-metadata')
def delete_election(election):
    """Delete election"""
    election.delete()
    db.session.commit()


@eperm('change-election-metadata')
def delete_group(group):
    """Delete election"""
    group.delete()
    db.session.commit()


def list_groups(running=None):
    """List election groups"""
    return ElectionGroup.query.all()


@rperm('create-election')
def make_election(**kw):
    """Create election."""
    return Election(**kw)


@rperm('create-election')
def make_group(**kw):
    """Create election group."""
    return ElectionGroup(**kw)


default_start_time = datetime.time(7, 0)
default_end_time = datetime.time(11, 0)
default_duration = datetime.timedelta(days=7)


def make_group_from_template(template_name, ou, principals=()):
    """Create election with elections from template"""
    current_app.logger.info('Make election group %s for %s',
                            template_name,
                            ou)
    import datetime
    import functools

    election_templates = current_app.config.get('ELECTION_TEMPLATES')

    #if current_app.config['AUTH_ENABLED'] and not \
    #        check_perms(principals, 'create-election', ou=ou):
    #    current_app.logger.info('Testing %s', principals)
    #    raise PermissionDenied()

    template = election_templates[template_name]
    name = template['name']
    group_type = template['settings']['group_type']
    elections = template['settings']['elections']
    metadata = template['settings']['rule_set']

    now = datetime.datetime.utcnow()

    def candidate_type(e):
        return metadata['candidate-type']

    def common_candidate_type():
        return functools.reduce(lambda x, y: x if x == y else None,
                                map(candidate_type, elections))

    def default_start():
        return datetime.datetime.combine(
            now.date(),
            default_start_time).replace(tzinfo=datetime.timezone.utc)

    def default_end():
        return datetime.datetime.combine(
            (now + default_duration).date(),
            default_end_time).replace(tzinfo=datetime.timezone.utc)

    def mandate_period_start(e):
        start = e['mandate_period'].get('start', '--01-01')

        if start.startswith('--'):
            # aniso8601 does not support extended year representation.
            # Let's try to fix that:
            start = str(now.year) + start[1:]

        date = aniso8601.parse_date(start)
        if date < now.date():
            date = date.replace(year=(now.year + 1))
        return date

    def mandate_period_end(e):
        start = mandate_period_start(e)
        length = e['mandate_period'].get('duration')
        if length is None:
            return None
        duration = aniso8601.parse_duration(length)
        return start + duration

    grp_name = dict()
    for lang in name.keys():
        grp_name[lang] = name[lang].format(ou.name[lang])

    group = ElectionGroup(name=grp_name,
                          description=None,  # Set this?
                          type=group_type,
                          meta=metadata,
                          ou=ou)

    def make_candidate_list(c):
        cand_list = ElectionList(name=c['name'])
        return cand_list

    def make_pollbook(kw):
        return PollBook(**kw)

    def make_election(e):
        if group_type == 'single_election':
            name = group.name
        else:
            name = e['name']
        election = Election(name=name,
                            sequence=e['sequence'],
                            election_group=group,
                            start=default_start(),
                            end=default_end(),
                            mandate_period_start=mandate_period_start(e),
                            mandate_period_end=mandate_period_end(e),
                            candidate_type=metadata['candidate_type'],
                            meta=metadata,
                            active=group_type == 'single_election',)
        election.lists = list(map(make_candidate_list, e['voter_groups']))
        election.pollbooks = list(map(make_pollbook, e['voter_groups']))
        return election

    group.elections = list(map(make_election, elections))

    db.session.add(group)
    db.session.commit()
    return group


make_group_from_template.is_protected = True
