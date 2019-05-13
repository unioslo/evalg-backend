#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging

from flask_allows import Allows
from werkzeug.exceptions import Forbidden

import evalg.authentication.user
import evalg.database.query

logger = logging.getLogger(__name__)


class PermissionDenied(Forbidden):
    pass


allows = Allows(
    identity_loader=lambda: evalg.authentication.user,
    throws=PermissionDenied)


def init_app(app):
    allows.init_app(app=app)
