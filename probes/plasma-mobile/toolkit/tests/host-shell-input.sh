#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Validate selected host shell before any configure or output creation.
set -eu
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-host-shell-test.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
export QT_HOST_TOOLS_PROFILE=quick CMAKE=/usr/bin/true NINJA=/usr/bin/true TAR=/usr/bin/true PATCH=/usr/bin/true HOST_PYTHON=/usr/bin/true WAYLAND_SCANNER=/usr/bin/true HOST_CC=/usr/bin/true HOST_CXX=/usr/bin/true HOST_DBUS_PREFIX=/tmp HOST_PACKAGE_PREFIX=/tmp HOST_PKG_CONFIG=/usr/bin/true
for shell in relative-shell "$work/missing"; do
    output=$(HOST_SH="$shell" /bin/sh "$cross/build-host-tools.sh" /tmp "$work/output" 2>&1) && { echo 'Invalid host shell accepted' >&2; exit 1; }
    case "$shell" in relative-shell) expected='Absolute paths required' ;; *) expected="Missing executable: $shell" ;; esac
    printf '%s\n' "$output" | grep -F -x "$expected" >/dev/null
    [ ! -e "$work/output" ] || { echo 'Invalid shell created output' >&2; exit 1; }
done
echo 'Host shell validation PASS'
