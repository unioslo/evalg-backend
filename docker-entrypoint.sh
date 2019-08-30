#!/bin/bash
set -e

echo "Starting rsyslogd"
/usr/sbin/rsyslogd
echo "Starting crond"
/usr/sbin/crond

exec "$@"
