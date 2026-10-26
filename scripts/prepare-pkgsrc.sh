#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted compatibility launcher.
set -eu
case "${PY:-}" in
    /*) ;;
    *) printf '%s\n' 'Set PY to the explicit Python executable.' >&2; exit 2 ;;
esac
case "$0" in
    */*) base=${0%/*} ;;
    *) base=. ;;
esac
exec "$PY" -B "$base/prepare-pkgsrc.py" "$@"
