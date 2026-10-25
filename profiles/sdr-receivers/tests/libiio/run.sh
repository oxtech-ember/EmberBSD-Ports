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

dl=
core=libiio.so.1
case "$(uname -s)" in Linux) dl=-ldl;; Darwin) core=libiio.1.dylib;; esac
"$CC" ${CFLAGS:-} -Wall -Wextra -Werror "$testdir/lifetime.c" ${LDFLAGS:-} $dl -o "$work/lifetime"
for library in libiio.so.0 "$core"; do
    "$work/lifetime" "$prefix/lib/$library" >> "$work/lifetime.log" 2>&1
done
cat "$work/lifetime.log"
echo 'PASS actual ABI0/ABI1 repeated load/unload and process exit'
