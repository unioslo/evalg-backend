#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Models and related tools and functionality. """
import datetime
import uuid

from evalg import db
from evalg.database.formatting import PrimaryKeyRepr


_model_repr = PrimaryKeyRepr(maxstring=50, maxother=50)


class Base(db.Model):
    __abstract__ = True

    def __repr__(self):
        return _model_repr.repr(self)
