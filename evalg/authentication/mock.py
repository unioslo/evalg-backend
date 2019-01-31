#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tools to mock:
 - being in front of a Dataporten Gatekeeper
 - fetching data from the Dataporten and Feide APIs as the mocked user

"""
import logging

from flask import request, current_app

from flask_feide_gk import gatekeeper


class MockGatekeeperData(gatekeeper.GatekeeperData):
    """
    Flask middleware component for mocking featching of Gatekeeper request data.

    Does not require any basic authentication.
    """
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pass

    def _get_mock_user(self, user_id=None):
        configured_user = current_app.config.get('AUTH_MOCK_LOGIN_AS', None)
        user_id = user_id or configured_user
        if not user_id:
            return {}
        data = current_app.config['FEIDE_MOCK_DATA']
        return data['users'].get(user_id)

    @property
    def user_id(self):
        return self._get_mock_user().get('id')

    @property
    def client_id(self):
        return current_app.config['FEIDE_MOCK_DATA']['client_id']

    @property
    def user_sec(self):
        return gatekeeper.UserIds(self._get_mock_user().get('sec'))

    @property
    def access_token(self):
        return ''

    def require(self, func):
        # We don't validate the request
        return func


class MockDataportenApi(object):
    def __init__(self, user, app=None):
        self.user = user
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pass

    @property
    def mock_user(self):
        data = current_app.config['FEIDE_MOCK_DATA']
        return data.get('users', {}).get(self.user.user_id)

    def get_user_info(self):
        return self.mock_user.get('feide_data')

    def get_user_photo(self):
        return ''