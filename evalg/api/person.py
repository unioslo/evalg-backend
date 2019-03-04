#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" The person API. """
from flask import Blueprint, make_response

from flask_apispec.views import MethodResource
from flask_apispec import use_kwargs, marshal_with
from flask_apispec import doc
from marshmallow import fields
from evalg import db, docs
from evalg.api import BaseSchema, add_all_authz
from evalg.person import (list_persons, make_person, get_person, update_person,
                          delete_person, search_person)

bp = Blueprint('persons', __name__)
add_all_authz(globals())


class PersonSchema(BaseSchema):
    id = fields.UUID()

    feide_user_id = fields.String()
    email = fields.String()
    feide_id = fields.String()
    first_name = fields.String()
    last_name = fields.String()
    last_update = fields.DateTime()
    nin = fields.String()
    username = fields.String()

    class Meta:
        strict = True
        dump_only = ('id', )


@doc(tags=['person'])
class PersonCollection(MethodResource):
    @marshal_with(PersonSchema(many=True))
    @doc(summary='Get persons')
    def get(self):
        return list_persons()

    @use_kwargs(PersonSchema())
    @marshal_with(PersonSchema(), code=201)
    @doc(summary='Create a person')
    def post(self, **kwargs):
        person = make_person(**kwargs)
        db.session.add(person)
        db.session.commit()
        return (person, 201)


@doc(tags=['person'])
class PersonDetail(MethodResource):
    @marshal_with(PersonSchema())
    @doc(summary='Get a person')
    def get(self, person_id):
        return get_person(person_id)

    @marshal_with(PersonSchema())
    @use_kwargs(PersonSchema())
    @doc(summary='Partially update a person')
    def patch(self, person_id, **kwargs):
        person = get_person(person_id)
        update_person(person, **kwargs)
        db.session.commit()
        return person

    @marshal_with(None, code=204)
    @doc(summary='Delete a person')
    def delete(self, person_id):
        person = get_person(person_id)
        delete_person(person)
        db.session.commit()
        return make_response('', 204)


bp.add_url_rule('/persons/',
                view_func=PersonCollection.as_view('PersonCollection'),
                methods=['GET', 'POST'])
bp.add_url_rule('/persons/<uuid:person_id>',
                view_func=PersonDetail.as_view('PersonDetail'),
                methods=['GET', 'PATCH', 'DELETE'])


@doc(tags=['person'])
class PersonSearch(MethodResource):
    @use_kwargs({'filter': fields.Str()}, locations=['query'])
    @marshal_with(PersonSchema(many=True))
    @doc(summary='Search for persons')
    def get(self, filter):
        return search_person(filter)


bp.add_url_rule('/persons/search/',
                view_func=PersonSearch.as_view('PersonSearch'),
                methods=['GET'])


def init_app(app):
    app.register_blueprint(bp)
    docs.spec.add_tag({
        'name': 'person',
        'description': 'Operations on persons'})
    docs.register(PersonCollection,
                  endpoint='PersonCollection',
                  blueprint='persons')
    docs.register(PersonDetail,
                  endpoint='PersonDetail',
                  blueprint='persons')
    docs.register(PersonSearch,
                  endpoint='PersonSearch',
                  blueprint='persons')
