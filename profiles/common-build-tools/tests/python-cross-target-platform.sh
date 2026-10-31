#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake python-cross-target-platform.sh PKGSRC MAKECONF TARGET_PYLIB
#
# Cross builds of Python extensions run the build host interpreter. Its
# extension suffixes and sysconfig.get_platform() named the build host, so
# py-zopfli built zopfli.abi3-darwin.so in a macosx wheel. Generate the
# cross sitecustomize.py of archivers/py-zopfli and check what setuptools
# selects with it and the recipe environment. TARGET_PYLIB is the target
# lib/python3.x directory that holds the target _sysconfigdata module.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_PYLIB" >&2; exit 2; }
recipe=$1/archivers/py-zopfli makeconf=$2 pylib=$3
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] && [ "$(bm -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: select a MAKECONF for a NetBSD cross build" >&2; exit 2; }
site=$(bm -V '${WRKDIR}/.pysite/sitecustomize.py')
python=$(bm -V '${TOOL_PYTHONBIN}')
hostplat=$(bm -V '${MAKE_ENV:M_PYTHON_HOST_PLATFORM=*:S/^_PYTHON_HOST_PLATFORM=//}')
bm clean >/dev/null 2>&1 || :
bm "$site" >/dev/null
status=0
out=$(env -u _PYTHON_HOST_PLATFORM ${hostplat:+_PYTHON_HOST_PLATFORM=$hostplat} \
	PYTHONPATH="${site%/*}:$pylib" "$python" -c '
import sysconfig, zlib, _ctypes
from setuptools.command.build_ext import get_abi3_suffix
from setuptools.command.bdist_wheel import get_platform
print(get_abi3_suffix(), get_platform(None), sysconfig.get_config_var("SOABI"))
') || { echo "FAIL: the cross interpreter does not start"; exit 1; }
bm clean >/dev/null 2>&1 || :
set -- $out
[ "$1" = .abi3.so ] || { echo "FAIL: stable-ABI suffix is $1"; status=1; }
case $2 in netbsd_*) ;; *) echo "FAIL: wheel platform tag is $2"; status=1 ;; esac
[ "$3" = cpython-315 ] || { echo "FAIL: SOABI is $3"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross Python extensions use the target suffix and platform ($1, $2)"
