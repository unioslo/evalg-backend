import abc
import csv
import io
import logging
import re

from pprint import pprint


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
    def find_identifier_type(cls, ids):
        """
        Find the identity type of a list of indentitys.

        All of the identifiers needs to be of the same type.
        """

        if not ids:
            return None

        try:
            [int(x) for x in ids]
        except ValueError:
            pass
        else:
            if len(set([len(x) for x in ids]) - set([10, 11])) == 0:
                return 'fnr'
            else:
                # File contains invalid fnrs
                return None

        if all(['@' in x for x in ids]):
            if all([cls.is_posix_username(x.split('@')[0]) for x in ids]):
                return 'feide_id'
            else:
                return None

        if any(['@' in x for x in ids]):
            # Probably a feide id or email mixed in with usernames
            return None

        if all([cls.is_posix_username(x) for x in ids]):
            return 'username'

        # No id type found
        return None

    @classmethod
    def check_and_rjust_fnr(cls, fnr):
        """
        Preform some rudimentary checks on a fnr.

        If the len is 10 we assume that a leading zero is missing.
        TODO: Validate the fnrs
        """
        try:
            int(fnr)
        except ValueError:
            return None

        if len(fnr) == 10:
            # Probably missing a leading zero.
            fnr = fnr.rjust(11, '0')
        elif len(fnr) < 10:
            # Invalid fnr
            return None

        return fnr

    @classmethod
    def is_posix_username(cls, username):

        pprint(username)
        valid_posix_username = '^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\\$)$'

        res = re.search(valid_posix_username, username)
        print(res)
        if res:
            pprint('True')
            return True
        else:
            pprint('False')
            return False

    @classmethod
    def is_fs_header(cls, header):
        if header.startswith('FS.PERSON.BRUKERNAVN'):
            return True

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
            parser = supported_mime_types[census_file.mimetype](
                census_file)

            if parser.id_type is None:
                # No supported id type in file
                return None
            return parser
        return None


class PlainTextParser(CensusFileParser):

    def __init__(self, census_file):
        super().__init__(census_file)
        content = self.census_file.read().decode('utf-8')
        self.fields = [x for x in content.split('\n') if x]

        if len(self.fields) > 0 and self.is_fs_header(self.fields[0]):
            # File is a csv file errorously save as .txt.
            self.census_file.seek(0)
            parser = CvsParser(self.census_file)
            self.fields = [x for x in parser.parse()]
            self.has_fs_header = True
        else:
            self.has_fs_header = False

        self._id_type = self.find_identifier_type(self.fields)

    @classmethod
    def get_mime_type(cls):
        return 'text/plain'

    @property
    def id_type(self):
        return self._id_type

    def parse(self):
        if not self.id_type:
            return None
        elif self.id_type == 'fnr':
            for fnr in self.fields:
                fnr = self.check_and_rjust_fnr(fnr)
                if fnr:
                    yield fnr
                else:
                    continue
        elif self.id_type == 'feide_id' or self.id_type == 'username':
            for x in self.fields:
                yield x
        else:
            return None


class CvsParser(CensusFileParser):

    def __init__(self, census_file):
        super().__init__(census_file)
        csvfile = io.StringIO(self.census_file.stream.read().decode('utf-8'))

        first_line = csvfile.readline()
        self.has_fs_header = self.is_fs_header(first_line)
        if not self.has_fs_header:
            # No fs header, move back to file start
            csvfile.seek(0)

        self.fields = [x[0] for x in csv.reader(csvfile) if x and x[0]]
        self._id_type = self.find_identifier_type(self.fields)


    @classmethod
    def get_mime_type(cls):
        return 'text/csv'

    @property
    def id_type(self):
        return self._id_type

    def parse(self):

        if not self._id_type:
            return None
        elif self.id_type == 'fnr':
            for fnr in self.fields:
                fnr = self.check_and_rjust_fnr(fnr)
                if fnr:
                    yield fnr
                else:
                    continue
        elif self.id_type == 'username' or self.id_type == 'feide_id':
            for x in self.fields:
                yield x
        else:
            return None
