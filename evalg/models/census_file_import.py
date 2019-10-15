import uuid

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import case, schema, sqltypes

import evalg.database.types
from .base import ModelBase


class CensusFileImport(ModelBase):
    """Database model for importing census files."""

    __versioned__ = {}
    __tablename__ = 'census_file_import'

    id = schema.Column(
        evalg.database.types.UuidType,
        default=uuid.uuid4,
        doc='a unique uuid for the census file import',
        primary_key=True,
    )

    pollbook_id = schema.Column(
        evalg.database.types.UuidType,
        schema.ForeignKey('pollbook_meta.id'),
        nullable=False)

    pollbook = relationship(
        'Pollbook',
        back_populates='census_file_imports')

    # Census file
    census_file = schema.Column(
        sqltypes.LargeBinary,
        doc='The census file',
    )

    mime_type = schema.Column(
        sqltypes.UnicodeText,
        doc='file mime type'
    )

    import_results = schema.Column(
        sqltypes.UnicodeText,
        doc='Results for the census file import',
    )

    initiated_at = schema.Column(evalg.database.types.UtcDateTime)
    finished_at = schema.Column(evalg.database.types.UtcDateTime)

    @hybrid_property
    def status(self):
        if self.finished_at:
            return 'finished'
        return 'ongoing'

    @status.expression
    def status(self):
        return case(
            [(self.finished_at.isnot(None), 'finished')],
            else_='ongoing')
