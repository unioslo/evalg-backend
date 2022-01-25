from typing import Dict
import evalg

import abc


class UnitImporter(metaclass=abc.ABCMeta):
    """Abstract class used to create OU importers."""

    subclasses: Dict = {}

    def __init__(self, config):
        self.config = config
        self.check_config()

    @abc.abstractmethod
    def get_units(self):
        """Unit generator."""

    @abc.abstractmethod
    def check_config(self):
        """Check if config is correct."""

    @classmethod
    def factory(cls, importer_type, config):
        """Returns the correct importer, if supported."""
        if importer_type not in cls.subclasses:
            return ValueError('Importer type not supported %s', importer_type)
        return cls.subclasses[importer_type](config)

    @classmethod
    def register(cls, importer_type):
        def decorator(subclass):
            cls.subclasses[importer_type] = subclass
            return subclass
        return decorator