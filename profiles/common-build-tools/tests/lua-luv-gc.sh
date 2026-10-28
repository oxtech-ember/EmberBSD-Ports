#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). luv survives Lua 5.5's garbage collector.
# Usage: lua-luv-gc.sh LUA LUV_CDIR LUV_SOURCE
# Run luv's own test suite from LUV_SOURCE (the extracted distfile) with
# the luv.so in LUV_CDIR under a stop-the-world collector (pause 0,
# stepmul 0), as luv's CI does. luv 1.52.1-0 crashes with SIGSEGV there
# after the fs tests (use after free); 1.53.0-0 passes every test.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 LUA LUV_CDIR LUV_SOURCE" >&2; exit 2; }
lua=$1 cdir=$2 src=$3
log=${TMPDIR:-/tmp}/lua-luv-gc.$$
cd "$src"
set +e
LUA_CPATH="$cdir/?.so" "$lua" -e "collectgarbage('incremental');
collectgarbage('param', 'pause', 0); collectgarbage('param', 'stepmul', 0)" \
    tests/run.lua > "$log" 2>&1
rc=$?
set -e
oks=$(grep -c '^ok ' "$log" || :)
bad=$(grep -c '^not ok ' "$log" || :)
if [ "$rc" != 0 ] || [ "$bad" != 0 ] || ! grep -q '^# All tests passed' "$log"; then
    echo "FAIL: luv tests under aggressive GC: exit $rc, $oks ok, $bad not ok"
    tail -5 "$log"; rm -f "$log"; exit 1
fi
rm -f "$log"
echo "PASS: luv tests under aggressive GC: $oks ok"
