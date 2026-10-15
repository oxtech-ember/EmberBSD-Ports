#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run unmodified upstream tests in private scratch.
set -eu
[ "$#" = 2 ] || { echo 'Usage: tdb-runtime.sh TEST_BUNDLE NEW_RESULTS' >&2; exit 2; }
bundle=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
result=$(CDPATH= cd -- "$2" && pwd)
mkdir "$result/scratch"
trap 'rm -rf "$result/scratch"' EXIT
trap 'exit 1' HUP INT TERM
ulimit -c 0
unset LD_LIBRARY_PATH PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=$result/scratch
export TEST_DATA_PREFIX=$result/scratch
cd "$result/scratch"
cp -R "$bundle/test" test
export BINDIR=/usr/pkg/bin
timeout -k 5 60 sh test/test_tdbbackup.sh test/jenkins-be-hash.tdb > "$result/backup.log" 2>&1
timeout -k 5 60 sh test/test_tdbdump.sh test/sample_tdb.tdb test/sample_tdb.txt test/sample_tdb_x.txt > "$result/dump.log" 2>&1
count=0
for test in "$bundle"/bin/tdb1-*; do
    name=$(basename "$test")
    timeout -k 5 120 "$test" > "$result/$name.log" 2>&1
    count=$((count + 1))
done
[ "$count" = 37 ]
timeout -k 5 180 "$bundle/bin/tdbtorture" -s 1 > "$result/torture.log" 2>&1
timeout -k 5 120 /usr/pkg/bin/python3.15 "$bundle/python/tests/simple.py" > "$result/python.log" 2>&1
printf 'PASS: two upstream CLI suites, %s C test programs, deterministic torture and installed Python binding\n' "$count"
