"""Database models related to private-key backup"""
import uuid


import evalg.database.types

from evalg import db
from evalg.utils import utcnow


from .base import ModelBase
from .election import ElectionGroup


class MasterKey(ModelBase):
    """
    Master-key

    Represents a master-key (public key) used to encrypt and hence backup
    election private keys.
    """
    __tablename__ = 'master_key'

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    description = db.Column(db.UnicodeText, nullable=False)

    public_key = db.Column(db.Text, nullable=False)

    active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(evalg.database.types.UtcDateTime, default=utcnow)

    def __str__(self):
        return str(self.public_key)


class ElectionGroupKeyBackup(ModelBase):
    """
    Encrypted ElectionGroup private-key

    Encrypted version of the private key corresponding to
    ElectionGroup.public_key
    """
    __tablename__ = 'election_group_key_backup'

    id = db.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        primary_key=True)

    encrypted_priv_key = db.Column(db.Text, nullable=False)

    election_group_id = db.Column(evalg.database.types.UuidType,
                                  db.ForeignKey('election_group.id'),
                                  nullable=False)
    election_group = db.relationship(
        ElectionGroup,
        backref='election_group_key_backups')

    master_key_id = db.Column(evalg.database.types.UuidType,
                              db.ForeignKey('master_key.id'),
                              nullable=False)
    master_key = db.relationship(MasterKey,
                                 backref='election_group_key_backups')

    active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(evalg.database.types.UtcDateTime, default=utcnow)

    def __str__(self):
        return str(self.encrypted_priv_key)
