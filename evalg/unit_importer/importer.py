
import evalg

import abc

from flask import Flask, current_app


class UnitImporter(metaclass=abc.ABCMeta):
    """Abstract class used to create OU importers."""
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
    @abc.abstractmethod
    def get_type(cls):
        """Get the importer type."""

    @classmethod
    def factory(cls, importer_type, config):
        """Returns the correct importer, if supported."""
        supported_types = {
            x.get_type(): x for x in UnitImporter.__subclasses__()
        }
        if importer_type in supported_types:
            return supported_types[importer_type](config)
        return None
