#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module:
 - bootstraps the flask-allows extension
 - makes the currently authenticated user available to flask-allows
 - defines a exceptions related to authorization
"""
import logging

from flask_allows import Allows
from werkzeug.exceptions import Forbidden

import evalg.authentication.user

logger = logging.getLogger(__name__)


class PermissionDenied(Forbidden):
    pass


allows = Allows(
    identity_loader=lambda: evalg.authentication.user,
    throws=PermissionDenied)


def init_app(app):
    allows.init_app(app=app)
