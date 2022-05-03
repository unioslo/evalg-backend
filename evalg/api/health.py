import logging
import re
import requests
import time

from celery import Celery
from flask import Blueprint, current_app, jsonify

from evalg import db

logger = logging.getLogger(__name__)
API = Blueprint("health", __name__)


def check_celery_health() -> bool:
    """Define the method here, to avoid circular imports in the celery worker."""
    from evalg.tasks.celery_worker import celery

    # TODO, remove the extra ping when after EVALG-1065
    try:
        celery.control.inspect().ping()
    except BrokenPipeError as e:
        logger.debug("Error in celery ping. Try reconnect. e=%s", e)

    return bool(celery.control.inspect().ping())


def check_feide_health() -> bool:
    """Simple check. Tests if auth.dataporten.no returns 200."""

    ret = requests.get("https://auth.dataporten.no")
    if ret.status_code == 200:
        return True

    return False


def check_database_health():
    try:
        # Check that we can execute a query
        db.session.execute("SELECT 1")
    except Exception as e:
        return False

    return True


ZABBIX_HEALTH_FILE_VERSION = 3
ZABBIX_HEALTH_COMPONENTS = (
    # <component-name>, <severity-if-down>, <func() -> True or False/Exception>
    # ("celery-worker", "high", check_celery_health),
    ("database", "high", check_database_health),
    ("feide", "high", check_feide_health),
)


def _time_ms() -> int:
    """current timestamp in milliseconds."""
    # Or `int(time.time_ns() / 1_000_000)`?
    return int(time.time() * 1000)


def _get_components():
    # Common components
    for component_info in ZABBIX_HEALTH_COMPONENTS:
        yield component_info


@API.route("/health")
def get_health_report():
    """
    Get a health report for Zabbix.

    Example report:
    ::
        {
            "metadata": {
                "updated": 1581397535091,
                "health-file-version": 3
            },
            "components": {
                "celery-worker": {"status": false, "severity": "high"},
                "database": {"status": true, "severity": "high"}
            }
        }
    """

    report = {
        "metadata": {
            "updated": _time_ms(),
            "health-file-version": ZABBIX_HEALTH_FILE_VERSION,
        },
        "components": {},
    }

    components = report["components"]
    for name, severity, check_component in _get_components():
        try:
            is_ok = check_component()
        except Exception as e:
            logger.error("health check failed for %s (%s)", name, str(e))
            is_ok = False

        components[name] = {
            "status": bool(is_ok),
            "severity": str(severity),
        }

    # Check backend health
    # Check worker health
    # Check that rabbitmq is responding

    return jsonify(report)


def init_api(app):
    """Register API blueprint."""
    app.register_blueprint(API)
