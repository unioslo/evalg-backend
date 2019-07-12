"""
Collection of database query utils.
"""
import logging

from sqlalchemy.sql import and_

logger = logging.getLogger(__name__)


class TooManyError(LookupError):
    # TODO:
    # - Is there an appropriate exception for this in sqlalchemy we could use?
    # - Is there a way to write queries that could deal with this?
    # - If not, we may want to move this to evalg.database, together with
    #   helper methods that deals with queries where this is useful behaviour.
    pass


class TooFewError(LookupError):
    pass


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
        raise TooFewError("No results for %r with condition %r" %
                          (model, filter_cond))
    else:
        raise TooManyError("Multiple results (%d) for %r with condition %r" %
                           (num, model, filter_cond))


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
    except TooFewError:
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
        raise TooManyError("Multiple results (%d) for %r with condition %r" %
                           (num, model, filter_cond))
