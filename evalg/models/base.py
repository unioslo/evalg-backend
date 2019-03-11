"""
Database model base classes.
"""
# import sqlalchemy_continuum
# from sqlalchemy_continuum.plugins import ActivityPlugin

import sqlalchemy_continuum

from evalg import db
from evalg.database import audit
from evalg.database.formatting import PrimaryKeyRepr

_model_repr = PrimaryKeyRepr(maxstring=50, maxother=50)


sqlalchemy_continuum.make_versioned(
    user_cls='Person',
    plugins=[
        audit.audit_plugin,
        audit.meta_plugin,
    ],
)


class ModelBase(db.Model):
    __abstract__ = True

    # TODO: Do not inherit from `db.Model` - we should de-couple our models
    # from flask-sqlalchemy

    def __repr__(self):
        return _model_repr.repr(self)
