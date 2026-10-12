#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), preserve target PLIST spelling on cross hosts.
set -eu
[ "$#" = 3 ] || { echo 'Usage: check-files-case.sh STAGE EXPECTED ADDED' >&2; exit 2; }
stage=$1 expected=$2 added=$3
[ -d "$stage" ] && [ -f "$expected" ] && [ -f "$added" ]
probe=$(mktemp -d "$stage/.pkgsrc-case.XXXXXX")
output=$added.case.$$
trap 'rm -f "$probe/probe" "$output"; rmdir "$probe"' EXIT
trap 'exit 1' HUP INT TERM
: > "$probe/probe"
# A case-sensitive stage already preserves the target spelling exactly.
[ -e "$probe/PROBE" ] || exit 0
LC_ALL=C; export LC_ALL
# Distinct target files that fold to one host path could have overwritten each
# other. Reject that ambiguity rather than approving a damaged package.
awk '
    FILENAME == ARGV[1] {
        key=tolower($0)
        if (key in spelling && spelling[key] != $0) {
            print "Ambiguous target files on case-insensitive stage: " spelling[key] " and " $0 > "/dev/stderr"
            failed=1
        }
        spelling[key]=$0
        next
    }
    { key=tolower($0); print (key in spelling ? spelling[key] : $0) }
    END { if (failed) exit 1 }
' "$expected" "$added" > "$output"
sort "$output" > "$added"
