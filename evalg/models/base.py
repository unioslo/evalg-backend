"""
Database model base classes.
"""

from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.manager import VersioningManager
from sqlalchemy_continuum.plugins import PropertyModTrackerPlugin

from evalg import db
from evalg.database import audit
from evalg.database.formatting import PrimaryKeyRepr
from evalg.database.types import UtcDateTime, IpAddressType, UuidType

_model_repr = PrimaryKeyRepr(maxstring=50, maxother=50)

# Use our own Transaction factory
versioning_manager = VersioningManager(
    transaction_cls=audit.EvalgTransactionFactory())

make_versioned(
    manager=versioning_manager,
    user_cls='Person',
    plugins=[
        audit.audit_plugin,
        audit.meta_plugin,
        PropertyModTrackerPlugin(),
    ],
)


class ModelBase(db.Model): # type: ignore
    __abstract__ = True

    # TODO: Do not inherit from `db.Model` - we should de-couple our models
    # from flask-sqlalchemy

    def __repr__(self):
        return _model_repr.repr(self)
