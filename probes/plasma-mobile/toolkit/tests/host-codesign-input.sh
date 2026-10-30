#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Darwin signing service is explicit and validated before writing work.
set -eu
# These isolated input/PLAN fixtures exercise the lower-level producer.
QT_HOST_LOCKED=1
export QT_HOST_LOCKED
[ "$(uname -s)" = Darwin ] || { echo 'SKIP: Darwin signing service'; exit 0; }
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-codesign-test.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
export QT_HOST_TOOLS_PROFILE=quick HOST_SH=/bin/sh CMAKE=/usr/bin/true NINJA=/usr/bin/true TAR=/usr/bin/true PATCH=/usr/bin/true HOST_PYTHON=/usr/bin/true WAYLAND_SCANNER=/usr/bin/true HOST_CC=/usr/bin/true HOST_CXX=/usr/bin/true HOST_DBUS_PREFIX=/tmp HOST_PACKAGE_PREFIX=/tmp HOST_PKG_CONFIG=/usr/bin/true HOST_MACOSX_DEPLOYMENT_TARGET=26.0
for value in relative-codesign "$work/missing" "$work/contains space"; do
    output=$(HOST_CODESIGN="$value" /bin/sh "$cross/build-host-tools.sh" /tmp "$work/output" 2>&1) && { echo 'Invalid codesign accepted' >&2; exit 1; }
    case "$value" in relative*) expected='Absolute paths required';; *' '*) expected='Use paths without shell metacharacters';; *) expected="Missing executable: $value";; esac
    printf '%s\n' "$output" | grep -F -x "$expected" >/dev/null
    [ ! -e "$work/output" ] || { echo 'Invalid codesign created output' >&2; exit 1; }
done
echo 'Darwin signing service path validation PASS'
