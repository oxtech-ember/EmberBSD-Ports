#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted installed CLI image and lifetime regression.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PREFIX UPSTREAM_SOURCE NEW_WORK" >&2; exit 2; }
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'All paths must be absolute.' >&2; exit 2 ;; esac
done
prefix=$1
source=$2
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
case "${JBIG_MEMCHECK:-no}" in yes|no) ;; *) exit 2 ;; esac
run() {
    if [ "${JBIG_MEMCHECK:-no}" = yes ]; then
        valgrind --error-exitcode=99 --leak-check=full --show-leak-kinds=all \
            --errors-for-leak-kinds=all --track-origins=yes "$@"
    else
        "$@"
    fi
}
run "$prefix/bin/jbgtopbm" "$source/examples/ccitt1.jbg" "$work/input.pbm"
run "$prefix/bin/pbmtojbg" "$work/input.pbm" "$work/encoded.jbg"
cmp "$source/examples/ccitt1.jbg" "$work/encoded.jbg"
run "$prefix/bin/jbgtopbm" "$work/encoded.jbg" "$work/decoded.pbm"
cmp "$work/input.pbm" "$work/decoded.pbm"
run "$prefix/bin/pbmtojbg85" "$work/input.pbm" "$work/encoded85.jbg"
run "$prefix/bin/jbgtopbm85" "$work/encoded85.jbg" "$work/decoded85.pbm"
cmp "$work/input.pbm" "$work/decoded85.pbm"
run "$prefix/bin/jbgtopbm85" -B 1 "$work/encoded85.jbg" "$work/bytewise.pbm"
cmp "$work/input.pbm" "$work/bytewise.pbm"
run "$prefix/bin/pbmtojbg" < "$work/input.pbm" > "$work/stdio.jbg"
run "$prefix/bin/jbgtopbm" < "$work/stdio.jbg" > "$work/stdio.pbm"
cmp "$work/input.pbm" "$work/stdio.pbm"
run "$prefix/bin/pbmtojbg85" < "$work/input.pbm" > "$work/stdio85.jbg"
run "$prefix/bin/jbgtopbm85" < "$work/stdio85.jbg" > "$work/stdio85.pbm"
cmp "$work/input.pbm" "$work/stdio85.pbm"
run "$prefix/bin/jbgtopbm" -d "$source/examples/ccitt1.jbg" > "$work/diagnostic.txt"
test -s "$work/diagnostic.txt"
run "$prefix/bin/pbmtojbg" -v "$work/input.pbm" "$work/verbose.jbg"
cmp "$source/examples/ccitt1.jbg" "$work/verbose.jbg"
run "$prefix/bin/pbmtojbg" "$source/examples/multi.pgm" "$work/multi.jbg"
run "$prefix/bin/jbgtopbm" "$work/multi.jbg" "$work/multi.pgm"
cmp "$source/examples/multi.pgm" "$work/multi.pgm"
printf '%s\n' 'PASS: 14 installed CLI cases, exact images, reference encoding and diagnostic output'
