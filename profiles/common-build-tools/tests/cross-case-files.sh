#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual staging-filesystem contract.
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-case-files.sh HELPER NEW_WORK' >&2; exit 2; }
helper=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir "$work/stage" "$work/stage/ThreadWeaver"
: > "$work/stage/ThreadWeaver/Job"
if [ ! -d "$work/stage/threadweaver" ]; then
    echo 'SKIP: case-insensitive filesystem branch requires such a host'
    printf '%s\n' "$work/stage/ThreadWeaver/Job" > "$work/added"
    cp "$work/added" "$work/expected"
    sh "$helper" "$work/stage" "$work/expected" "$work/added"
    cmp "$work/expected" "$work/added"
    exit 0
fi
: > "$work/stage/threadweaver/job.h"
printf '%s\n' "$work/stage/ThreadWeaver/Job" "$work/stage/threadweaver/job.h" \
    > "$work/expected"
find "$work/stage" -type f | sort > "$work/added"
cp "$work/added" "$work/original"
if cmp -s "$work/expected" "$work/added"; then
    echo 'Fixture failed to reproduce the original mismatch' >&2; exit 1
fi
sh "$helper" "$work/stage" "$work/expected" "$work/added"
cmp "$work/expected" "$work/added"
: > "$work/stage/unlisted.h"
find "$work/stage" -type f | sort > "$work/added"
sh "$helper" "$work/stage" "$work/expected" "$work/added"
grep -Fxq "$work/stage/unlisted.h" "$work/added"
printf '%s\n' "$work/stage/ThreadWeaver/JOB" >> "$work/expected"
cp "$work/added" "$work/before-rejection"
if sh "$helper" "$work/stage" "$work/expected" "$work/added" > "$work/ambiguous.log" 2>&1; then
    echo 'Overwritable target file collision was accepted' >&2; exit 1
fi
cmp "$work/before-rejection" "$work/added"
grep -q 'Ambiguous target files' "$work/ambiguous.log"

# OpenSSL emits case-only manual aliases. Preserve aliases that point to one
# staged symlink target and the two names generated from one POD page.
man3=$work/stage/usr/pkg/man/man3
mkdir -p "$man3"
target=$man3/OpenSSL_version.3
upper=$man3/OPENSSL_VERSION_MAJOR.3
lower=$man3/OPENSSL_version_major.3
: > "$target"
ln -s OpenSSL_version.3 "$upper"
if [ ! -e "$lower" ]; then
    ln -s OpenSSL_version.3 "$lower"
fi
printf '%s\n%s\n' "$upper" "$lower" > "$work/alias-expected"
printf '%s\n' "$upper" > "$work/alias-added"
sh "$helper" "$work/stage" "$work/alias-expected" "$work/alias-added"
cmp "$work/alias-expected" "$work/alias-added"

trace_upper=$man3/OSSL_TRACE_ENABLED.3
trace_lower=$man3/OSSL_trace_enabled.3
printf '.SH NAME\nOSSL_trace_enabled, OSSL_TRACE_ENABLED\n' > "$trace_upper"
if [ ! -e "$trace_lower" ]; then
    cp "$trace_upper" "$trace_lower"
fi
printf '%s\n%s\n' "$trace_upper" "$trace_lower" > "$work/trace-expected"
printf '%s\n' "$trace_upper" > "$work/trace-added"
sh "$helper" "$work/stage" "$work/trace-expected" "$work/trace-added"
cmp "$work/trace-expected" "$work/trace-added"
echo 'PASS: case-preserving paths, OpenSSL aliases, extra files and collision rejection'
