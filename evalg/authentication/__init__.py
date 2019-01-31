#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - bootstraps the flask-feide-gatekeeper extension
 - ensures requests are originating from a gatekeeper
 - makes gatekeeper data available
 - provides a client to the Feide and Dataporten APIs
 - provides an object with information about the currently logged in user
"""
import logging

from flask_feide_gk import basic_auth
from flask_feide_gk import client
from flask_feide_gk import gatekeeper
from flask_feide_gk import utils

from evalg import db

from evalg.authentication import mock
from evalg.authentication.user import EvalgUser

logger = logging.getLogger(__name__)

# validator for credentials from the app config
creds = basic_auth.ConfigBackend()

# basic auth middleware
basic = basic_auth.BasicAuth(creds)

# feide gatekeeper headers
gk_user = None

# feide api client
feide_api = None

# authenticated user
user = None


def init_app(app):
    auth_method = app.config['AUTH_METHOD']
    if auth_method == 'feide':
        creds.init_app(app)
        basic.init_app(app)
        gk_user = gatekeeper.GatekeeperData(basic)
        feide_api = client.DataportenApi(gatekeeper_user)
    elif auth_method == 'mock':
        gk_user = mock.MockGatekeeperData(basic)
        feide_api = mock.MockDataportenApi(gk_user)
    else:
        raise NotImplementedError('Unknown AUTH_METHOD %r'.format(auth_method))

    user = EvalgUser(gk_user, feide_api, app)
