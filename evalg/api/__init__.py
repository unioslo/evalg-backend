#!/usr/bin/env python
# -*- coding: utf-8 -*-
import inspect
from functools import wraps
from flask import jsonify, g
from .. import ma, apierror
from ..apierror import ApiError
from marshmallow import SchemaOpts, ValidationError, fields, validates_schema


class NotFoundError(ApiError):
    code = 404
    error_type = 'not-found'


class BadRequest(ApiError):
    code = 400
    error_type = 'bad-request'


def handle_endpoint_not_found(err):
    return jsonify({
        'error': 'not-found',
        'details': 'No matching endpoint'
    }), 404


def handle_unprocessable_entity(err):
    data = getattr(err, 'data', {})
    messages = data.get('messages', ['Invalid request'])
    return jsonify({
        'messages': messages,
    }), 422


class BaseSchemaOpts(SchemaOpts):
    """ Extra Meta options for BaseSchema. """
    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.allow_unknown_fields = getattr(meta, 'allow_unknown_fields',
                                            False)


class BaseSchema(ma.Schema):
    OPTIONS_CLASS = BaseSchemaOpts

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data):
        if self.opts.allow_unknown_fields:
            return
        unknown = set(original_data) - set(self.fields)
        if unknown:
            raise ValidationError("Unknown field", unknown)


class TranslatedString(object):
    """ Dynamically generated schema with a field per configured language. """
    klass = None

    @classmethod
    def translation_fields(cls, languages):
        """ Generate a marshmallow string field per language. """
        return {lang: fields.Str(description=name)
                for lang, name in languages.items()}

    @classmethod
    def configure(cls, app):
        cls.klass = type('TranslatedString',
                         (BaseSchema, ),
                         cls.translation_fields(app.config['LANGUAGES']))

    def __new__(cls, **kwargs):
        return cls.klass(**kwargs)


def get_principals():
    """Return list of users principals."""
    # TODO: return g.principals or something
    # This is testing code
    import evalg.auth
    from evalg import db
    if evalg.auth.Permission is None:
        evalg.auth.init_auth()
        if not evalg.auth.Permission.query.all():
            for p in evalg.auth.Permission.permissions:
                db.session.add(p)
            role = evalg.auth.RoleList(role='root', name={'nb': 'superuser'},
                                       perms=evalg.auth.Permission.permissions)
            db.session.add(role)
            p = evalg.auth.PersonPrincipal(person_id='test')
            db.session.add(p)
            db.session.add(evalg.auth.Role(trait=role, principal=p))
            db.session.commit()

    return evalg.auth.Principal.query.all()
    return []
    return g.principals


def add_authz(module=None, *functions):
    """ Replace functions with a function where principals is set. """
    def authzd(f):
        @wraps(f)
        def fun(*args, **kw):
            #current_app.logger.info('%s(*%s, **%s)', f.__name__, args, kw)
            kw['principals'] = get_principals()
            return f(*args, **kw)
        return fun
    ret = [authzd(f) for f in functions]
    for f, ff in zip(functions, ret):
        (module or inspect.getmodule(f).__dict__)[f.__name__] = ff
    return ret


def add_all_authz(moduleglobals):
    """Lookup all functions in module with authz."""
    for v in moduleglobals.values():
        try:
            if getattr(v, 'is_protected', False):
                add_authz(moduleglobals, v)
        except:
            pass


def init_app(app):
    # Error handlers
    apierror.init_app(app)
    app.register_error_handler(422, handle_unprocessable_entity)
    app.register_error_handler(404, handle_endpoint_not_found)

    # Configure languages
    TranslatedString.configure(app)

    # Configure blueprints
    from . import (election,
                   election_list,
                   ou,
                   candidate,
                   election_template,
                   voter,
                   pollbook,
                   person,
                   group,
                   authz,
                   upload_census_file)
    election.init_app(app)
    election_list.init_app(app)
    ou.init_app(app)
    election_template.init_app(app)
    candidate.init_app(app)
    voter.init_app(app)
    pollbook.init_app(app)
    person.init_app(app)
    group.init_app(app)
    authz.init_app(app)
    upload_census_file.init_app(app)
