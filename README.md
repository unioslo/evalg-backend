# eValg – Internet voting for the University of Oslo

## Introduction

In 2006, the University of Oslo decided that its elections should be
electronic. For such, an web application was developed. Now (2017),
this web application is old, and it builds upon an unmaintained,
framework. Therefore it was decided to modernize the electronic voting
application.

## Principles

The new version builds upon the same principles as the old version:

* One should be permitted to vote several times, overwriting previous
  votes
* Votes should be encrypted and stored in a different location from
  the rest of the data
* A person should only be allowed to submit one single counting vote.
  If the same person logs in with different user ID's, they should
  be linked to the same voter (using whatever ID possible).

## Versioning

The first stable release of this software will become eValg 3.0, as 2.x
was the older software. Versioning is done by tagging git commits and is
automatically picked up by `setuptools_scm`.

See https://github.com/pypa/setuptools_scm

The tag should start with the letter v (for version), and then follow the
syntax of PEP 440, normally `vX.Y.Z`, where here X, Y and Z are numbers,
Y and Z being optional. Optionally, we can use the «aN», «bN» or «rcN» and the
other possibilities in PEP 440. The version should follow semantic versioning
guidelines.

## Install
To run the installer, you'll need a new version of setuptools::

```
pip install -U setuptools
```

To install the module using the setup script, you'll need to run::

```
pip install .
# OR
python setup.py install
```

## Run

To run one of the applications using `gunicorn`:

```
gunicorn evalg:wsgi
# OR
gunicorn ballotbox:wsgi
```

To run one of the applications using the builtin Flask server:

```
export FLASK_APP=evalg.wsgi  # or ballotbox.wsgi
flask run
# see: flask run --help
```

## Configuration

`evalg` and `ballotbox` first loads the `default_config.py` file found in the
package directory. Override settings defined here by:

1. Creating `evalg_config.py` or `ballotbox_config.py` in the
   `app.instance_path`
2. Putting a config file path in the environment variables `EVALG_CONFIG` or
   `BALLOTBOX_CONFIG`

## Development environment
A small development environment can be started with docker. This consists of
two containers, one for the database and one for the Flask-application.

The Flask application auto-reloads its code when you edit files on your docker host.

### Start the development environment
1. Copy `instance/evalg_config.py.example.dev` to `instance/evalg_config.py`.
2. `docker-compose -f docker-compose-evalg-dev.yaml up`
3. Initialize database: `docker exec -it evalg_evalg_1 flask db init`
3. Create appropriate database definitions (if the model has changed): `docker exec -it evalg_evalg_1 flask db migrate`
4. Apply said definitions: `docker exec -it evalg_evalg_1 flask db upgrade`

You can also `docker exec -it evalg_evalg_1 flask db downgrade base` to empty the database.

### Add example data to the database
If you want to populate the database with example data, run `docker exec -it
evalg_evalg_1 flask populate-tables`.

Run the commands `flask db downgrade` and `flask db upgrade` on beforehand if
you would like to clean before populating.

#### Example data definitions
In evalg/fixtures, there are located a series of JSON files. These files define
the example data. These files must be mentioned in an appropriate order in
evalg/fixtures/populate_tables.py.

See also https://pypi.python.org/pypi/Flask-Fixtures for more details.

### Alembic migration scripts
Alembic is used to upgrade the database on changes of the data model. Migration
data resides in the folder `evalg/migrations`, and can be generated with the
command `flask db migrate`, and applied with `flask db upgrade`.

### Flask shell
You can run the flask shell in order to do migrations and run commands defined
by the application:
```
docker exec -it evalg_evalg_1 flask
```

### A Postgres client
If you should like to use psql:
```
docker exec -u postgres -it evalg_db_1 psql
```

## Flask Shell

The flask shell command also comes with a shell utility:

```
FLASK_APP=evalg.wsgi flask shell
```

See http://flask.pocoo.org/docs/latest/shell/

## Import units from SAP

Units can be imported from the SAP-WS with the following command.

```
FLASK_APP=evalg.wsgi flask import-units
```

Or if running docker.
```
docker exec -it evalg_evalg_1 flask import-units
```

Config in evalg\_config.py:
```
UNIT_IMPORTER = { 
    'type': 'UIOSAPWS',
    'config': {
            'base_url': <URI>,
            'api_key': <SAP_API_KEY>,
        'root_ou': <ROOT_OU_NR>,
    }   
}
```


## Other CLI commands

This lists all CLI commands an application has to offer:

```
FLASK_APP=evalg.wsgi flask --help
```

