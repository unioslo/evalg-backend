"""
Collection of database query utils.
"""
import logging

from sqlalchemy.sql import and_
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

logger = logging.getLogger(__name__)


def lookup(session, model, **attrs):
    """
    Find a unique object identified by a set of attributes.

    :param session: An SQLAlchemy session
    :param model: An SQLAlchemy model to find
    :param attrs:
        A set of column names and values to use for matching.
    """
    conditions = tuple(
        getattr(model, attr) == attrs[attr]
        for attr in attrs)
    filter_cond = and_(*conditions)

    query = session.query(model).filter(filter_cond)
    num = query.count()
    if num == 1:
        obj = query.first()
        logger.debug('found %r object %r', model, obj)
        return obj
    elif num == 0:
        raise NoResultFound("No results for %r with condition %r" %
                            (model, filter_cond))
    else:
        raise MultipleResultsFound(
            "Multiple results (%d) for %r with condition %r" % (
                num, model, filter_cond))


def lookup_or_none(session, model, **attrs):
    """
    Find a unique object identified by a set of attributes.
    Return `None` if none is found.

    :param session: An SQLAlchemy session
    :param model: An SQLAlchemy model to find
    :param attrs:
        A set of column names and values to use for matching.
    """
    try:
        return lookup(session, model, **attrs)
    except NoResultFound:
        return None
    except Exception:
        # reraise any other exception
        raise
    assert False, 'not reached'


def get_or_create(session, model, **attrs):
    """
    Find or create a unique object identified by a set of attributes.

    .. note::
        Created objects are not added to the database session, so this function
        is is really only useful if you *know* you're going to mutate the
        result.

        Otherwise you'll have to check the object state to figure out
        if it needs to be added to the database session
        (https://docs.sqlalchemy.org/en/latest/orm/session_state_management.html),
        and at that point it might be easier to *not* use this function.

    :param session: An SQLAlchemy session
    :param model: An SQLAlchemy model to find
    :param attrs:
        A set of column names and values to use for matching. If a matching
        object is not found, it will be created using these values.
    """
    conditions = tuple(
        getattr(model, attr) == attrs[attr]
        for attr in attrs)
    filter_cond = and_(*conditions)

    query = session.query(model).filter(filter_cond)
    num = query.count()
    if num == 0:
        obj = model(**attrs)
        logger.debug('created new %r object %r', model, obj)
        return obj
    elif num == 1:
        obj = query.first()
        logger.debug('found existing %r object %r', model, obj)
        return obj
    else:
        raise MultipleResultsFound(
            "Multiple results (%d) for %r with condition %r" % (
                num, model, filter_cond))
