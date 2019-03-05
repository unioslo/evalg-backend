# evalg – electronic voting at the University of Oslo

Evalg 3 is a re-implementation of the electronic voting system used at the
University of Oslo.

This python-package is the backend of this voting system. It provides APIs for
managing elections, and for voting. You may want to have a look at the [evalg
frontend][repo_frontend] as well.


## Install

```
# make sure setuptools is up to date
pip install -U setuptools

# install (in editable mode if you're developing)
pip install [-e] .
```

You can read more about [installing evalg][doc_install] in the documentation.


## Configure

You can override any setting in [`default_config.py`](evalg/default_config.py)
by placing an `evalg_config.py` in the Flask instance folder. This folder is
either:

- `./instance/` (when running evalg from the repo)
- `<sys-prefix>/evalg-instance/` (when running from an installed package)

Or you can create a directory wherever and provide the path to it using the
`EVALG_CONFIG` environment variable.

The documentation has more information about configuring evalg:

- [configuring evalg][doc_config]
- [configuring authentication][doc_auth]


## Run

```
# with the flask dev server
FLASK_APP=evalg.wsgi flask run

# with gunicorn
gunicorn evalg:wsgi
```


## Development environment

To get started with a dev environment, check out the following documents:

- [Getting started][doc_dev_intro]
- [Basic dev-environment][doc_dev_local]
- [Using Docker][doc_dev_docker]


## Database

Before starting the evalg api (this application), you'll need a database, and
you'll need to initialize that database with the evalg database schemas

```
FLASK_APP=evalg.wsgi flask db upgrade
```

If you already have a database, and want to upgrade evalg to a later version,
you may have to migrate the database.  This is usually done with the same
_upgrade_-command.

If you want to try out some local database change, you'll have to build
migrations scripts first. This is done using `flask db migrate` - which will
place an additional migration script in `evalg/migrations/versions/`. You should
manually inspect (and adopt) the new script before running _upgrade_.

TODO: Database documentation?


  [repo_frontend]: https://bitbucket.usit.uio.no/projects/EVALG/repos/evalg-frontend/
  [doc_config]: docs/source/config.rst
  [doc_auth]: docs/source/auth.rst
  [doc_dev_docker]: docs/source/dev/docker-env.rst
  [doc_dev_local]: docs/source/dev/local-env.rst
  [doc_dev_intro]: docs/source/dev/getting-started.rst
  [doc_install]: docs/source/install.rst
