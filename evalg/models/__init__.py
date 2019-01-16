#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Models and related tools and functionality. """

from evalg import db


class Base(db.Model):
    __abstract__ = True

    def _get_repr_fields(self):
        return

    def __repr__(self):
        fields = self._get_repr_fields()
        if fields:
            data = ' '.join('{0}={1}'.format(str(f), repr(v))
                            for f, v in fields)
        else:
            data = 'at 0x{addr:02x}'.format(addr=id(self))
        return '<{cls.__module__}.{cls.__name__} {data}>'.format(
                cls=type(self),
                data=data)
