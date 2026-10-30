#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check a real Darwin host Qt configure and its resume guard.
set -eu
# These isolated input/PLAN fixtures exercise the lower-level producer.
QT_HOST_LOCKED=1
export QT_HOST_LOCKED
[ "$#" = 3 ] || { echo 'Usage: host-deployment-target.sh DISTFILES WORK EXPECTED_TARGET' >&2; exit 2; }
distfiles=$1 work=$2 expected=$3
HOST_SH=${HOST_SH:-/bin/sh}
export HOST_SH
case "$(uname -s)" in Darwin) ;; *) echo 'Darwin required' >&2; exit 2;; esac
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
grep -F -x "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=$expected" "$work/qtbase/CMakeCache.txt" >/dev/null
grep -F -x "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=$expected" "$work/qtbase/src/tools/syncqt/configure_time_bins/CMakeCache.txt" >/dev/null
grep -F -x "host_deployment_target=$expected" "$work/inputs.txt" >/dev/null
HOST_MACOSX_DEPLOYMENT_TARGET=$expected RESUME=1 QT_HOST_TOOLS_PLAN_ONLY=1 \
    "$HOST_SH" "$cross/build-host-tools.sh" "$distfiles" "$work" >/dev/null
different=99.0
[ "$expected" != "$different" ] || different=98.0
output=$(HOST_MACOSX_DEPLOYMENT_TARGET=$different RESUME=1 QT_HOST_TOOLS_PLAN_ONLY=1 \
    "$HOST_SH" "$cross/build-host-tools.sh" "$distfiles" "$work" 2>&1) && {
    echo 'Changed deployment target was accepted' >&2; exit 1
}
printf '%s\n' "$output" | grep -F -x 'Host deployment target changed; use a new work directory' >/dev/null
 echo 'Host deployment target and incompatible resume checks passed'
