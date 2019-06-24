# -*- coding: utf-8 -*-
"""Base classes for the counting package"""
import json


class Result:
    """
    The base class representing counting result
    """
    def __init__(self, meta):
        """
        :param meta: The metadata for this result
        :type meta: dict
        """
        self.meta = meta

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

    def to_json(self):
        """
        Returns a json representation of the object

        :return: JSON representation of the object
        :rtype: str
        """
        return json.dumps(self.__dict__)
