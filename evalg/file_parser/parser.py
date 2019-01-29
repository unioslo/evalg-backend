import abc


class CensusFileParser(metaclass=abc.ABCMeta):
    def __init__(self, census_file):
        self.census_file = census_file

    @abc.abstractmethod
    def parse(self):
        """Parse the current file and create a generator"""

    @property
    @abc.abstractmethod
    def id_type(self):
        """Get the id type returned by the generator"""

    @classmethod
    @abc.abstractmethod
    def get_mime_type(cls):
        """Get the mimetype supported by the parser."""

    @classmethod
    def get_supported_mime_types(cls):
        return [x.get_mime_type() for x in CensusFileParser.__subclasses__()]

    @classmethod
    def factory(cls, census_file):
        """Returns the correct file parser if supported."""
        supported_mime_types = {
            x.get_mime_type(): x for x in CensusFileParser.__subclasses__()
        }

        if census_file.mimetype in supported_mime_types:
            return supported_mime_types[census_file.mimetype](
                census_file)
        return None


class PlainTextParser(CensusFileParser):

    def __init__(self, census_file):
        super().__init__(census_file)
        content = self.census_file.stream.read().decode("utf-8")
        self.fields = [x for x in content.split("\n") if x]
        self._id_type = self.find_identifier_type()

    @classmethod
    def get_mime_type(cls):
        return "text/plain"

    @property
    def id_type(self):
        return self._id_type

    def find_identifier_type(self):
        # Check if fnr
        try:
            [int(x) for x in self.fields]
            if len(set([len(x) for x in self.fields]) - set([10, 11])) == 0:
                return "fnr"
        except ValueError:
            pass
        # Check if Feide ID
        if all(["@" in x for x in self.fields]):
            return "feide_id"
        if all([' ' not in x for x in self.fields]):
            # Assume username
            return "username"
        raise TypeError

    def parse(self):

        if self.id_type == None:
            return None
        elif self.id_type == "fnr":
            for fnr in self.fields:
                try:
                    int(fnr)
                except ValueError:
                    continue
                if len(fnr) == 10:
                    # Probably missing a leading zero.
                    fnr = fnr.rjust(11, "0")
                elif len(fnr) < 10:
                    # Invalid fnr
                    continue
                yield fnr
        elif self.id_type == "feide_id":
            for feide_id in self.fields:
                yield feide_id
        elif self.id_type == "username":
            for username in self.fields:
                yield username
