#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" = 2 ] || { echo 'Usage: run.sh INSTALLED_PREFIX NEW_WORK' >&2; exit 2; }
: "${CC:?Select the absolute GCC16 compiler}"
: "${PY:?Select the absolute Python interpreter}"
prefix=$1
work=$2
[ ! -e "$work" ] || exit 2
mkdir -p "$work"
testdir=$(CDPATH= cd "$(dirname "$0")" && pwd)
# CFLAGS/LDFLAGS are caller-selected diagnostic flags; no implicit compiler.
"$CC" ${CFLAGS:-} -pthread -Wall -Wextra -Werror -I"$prefix/include/iio-compat-0" \
    "$testdir/abi0.c" "$prefix/lib/libiio.so.0" ${LDFLAGS:-} -o "$work/abi0"
export DYLD_LIBRARY_PATH="$prefix/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$PY" "$testdir/legacy.py" "$work/abi0" > "$work/contract.log" 2>&1
cat "$work/contract.log"
