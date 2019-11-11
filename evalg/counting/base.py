# -*- coding: utf-8 -*-
"""Base classes for the counting package"""
import json

from jinja2 import Environment, PackageLoader


class RoundState:
    """
    RoundState-class.

    Represents the state of the round after a the count is performed.
    """

    def __init__(self, round_obj):
        """
        :param round_obj: The round-counting object
        :type round_obj: object
        """
        self._final = False
        self._round_obj = round_obj
        self._elected = tuple()  # tuple of candidates elected in this round
        self._events = []

    @property
    def all_elected_candidates(self):
        """all_elected_candidates-property"""
        # should be probably overloaded
        return self._elected

    @property
    def all_elected_substitutes(self):
        """all_elected_substitutes-property"""
        # We want to please the ElectionPath API
        return tuple()

    @property
    def elected(self):
        """elected-property"""
        return self._elected

    @property
    def events(self):
        """events-property"""
        return tuple(self._events)

    @property
    def final(self):
        """final-property"""
        return self._final

    @final.setter
    def final(self, value):
        """final-property setter"""
        self._final = value

    @property
    def round_obj(self):
        """round_obj-property"""
        return self._round_obj

    def add_elected_candidate(self, candidate):
        """
        Sets self._elected to a new tuple containing `candidate`

        :param candidate: Candidate object
        :type candidate: object
        """
        self._elected = self._elected + (candidate, )

    def add_event(self, event):
        """
        Adds a new CountingEvent into the state

        :param event: The CountingEvent object
        :type event: CountingEvent
        """
        self._events.append(event.to_dict())


class Result:
    """The base class representing counting result"""

    def __init__(self, meta):
        """
        :param meta: The metadata for this result
        :type meta: dict
        """
        self.meta = meta

    @classmethod
    def from_dict(cls, dict_obj):
        """
        Returns a Result object from the dict-object

        :param dict_obj: The dict object
        :type dict_obj: dict

        :return: A new Result-object
        :rtype: base.Result
        """
        return cls(**dict_obj)

    @classmethod
    def from_json(cls, json_str):
        """
        Returns a Result object from the json-string

        :param json_str: The JSON string
        :type json_str: str

        :return: A new Result-object
        :rtype: base.Result
        """
        return cls(**json.loads(json_str))

    def to_dict(self):
        """
        Returns a dict representation of the object

        :return: dict representation of the object
        :rtype: dict
        """
        return self.__dict__

    def to_json(self):
        """
        Returns a json representation of the object

        :return: JSON representation of the object
        :rtype: str
        """
        return json.dumps(self.__dict__)


class Protocol:
    """The base class representing counting protocol"""

    def __init__(self, meta):
        """
        :param meta: The metadata for this protocol
        :type meta: dict
        """
        self.meta = meta

    @classmethod
    def from_dict(cls, dict_obj):
        """
        Returns a Protocol object from the dict-object

        :param dict_obj: The dict object
        :type dict_obj: dict

        :return: A new Protocol-object
        :rtype: base.Protocol
        """
        return cls(**dict_obj)

    @classmethod
    def from_json(cls, json_str):
        """
        Returns a Protocol object from the json-string

        :param json_str: The JSON string
        :type json_str: str

        :return: A new Protocol-object
        :rtype: base.Protocol
        """
        return cls(**json.loads(json_str))

    def to_dict(self):
        """
        Returns a dict representation of the object

        :return: dict representation of the object
        :rtype: dict
        """
        return self.__dict__

    def to_json(self):
        """
        Returns a json representation of the object

        :return: JSON representation of the object
        :rtype: str
        """
        return json.dumps(self.__dict__, indent=4)

    def render(self, template='protocol.tmpl'):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used (default: protocol.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        tmpl = Environment(
            newline_sequence='\r\n',
            loader=PackageLoader('evalg.counting', 'templates')).get_template(
                template)
        return tmpl.render(**self.to_dict())
