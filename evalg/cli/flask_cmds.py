"""
Commands for showing flask parameters.

This module extend the existing flask cli with custom commands that show flask
settings and routes.
"""
import click
import flask
import flask.cli


@click.command('show-config',
               short_help='Print flask configuration.')
@flask.cli.with_appcontext
def show_config():
    print("Settings:")
    for setting in sorted(flask.current_app.config):
        print(
            "  {setting}: {value}".format(
                setting=str(setting),
                value=repr(flask.current_app.config[setting])))


@click.command('show-routes',
               short_help='Print flask routing rules.')
@flask.cli.with_appcontext
def show_routes():
    print("Routes:")
    for rule in flask.current_app.url_map.iter_rules():
        print("  {!r}".format(rule))


commands = tuple((
    show_config,
    show_routes,
))


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
