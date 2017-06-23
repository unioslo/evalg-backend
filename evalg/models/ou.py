#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Models for organizational units. """

import uuid
from evalg import db
from evalg.models import Base
from sqlalchemy_utils import UUIDType, JSONType


class OrganizationalUnit(Base):
    id = db.Column(UUIDType, default=uuid.uuid4, primary_key=True)
    name = db.Column(JSONType, nullable=False)
    external_id = db.Column(db.Text, nullable=False, unique=True)
    deleted = db.Column(db.Boolean, default=False)
    tag = db.Column(db.String, nullable=False)

    def isunder(self, other, acceptsame=True):
        """ Checks if self is a sub ou of other. """

        if isinstance(other, OrganizationalUnit):
            other = other.id
        if self.id == other:
            return True
        if self.parent_id is None:
            return False
        return self.parent.isunder(other)

    def __lt__(self, other):
        """ Checks if self is a sub ou of other. """

        return self.isunder(other, acceptsame=False)

    def __le__(self, other):
        """ Checks if self is a sub ou of other. """

        return self.isunder(other, acceptsame=True)

    def isover(self, other, acceptsame=True):
        """ Checks if other is a sub ou of self. """

        if isinstance(other, OrganizationalUnit):
            return other.isunder(self.id)
        return other in self.subous(acceptsame)

    def __gt__(self, other):
        return self.isover(other, acceptsame=False)

    def __ge__(self, other):
        return self.isover(other, acceptsame=True)

    def __eq__(self, other):
        """ Checks for equality between ous. """

        return isinstance(other, OrganizationalUnit) and self.id == other.id

    def subous(self, includeself=True):
        """ Generates all children, grandchildren and so on of self. """
        queue = [self] if includeself else self.children[:]
        while queue:
            front = queue.pop()
            yield front
            queue.extend(front.children)
