#!/bin/bash
set -e

echo "Starging rsyslogd"
/usr/sbin/rsyslogd

exec "$@"
