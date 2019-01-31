"""
Database model base classes.
"""
from evalg import db
from evalg.database.formatting import PrimaryKeyRepr

_model_repr = PrimaryKeyRepr(maxstring=50, maxother=50)


class ModelBase(db.Model):
    __abstract__ = True

    def __repr__(self):
        return _model_repr.repr(self)
