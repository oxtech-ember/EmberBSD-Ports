#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exact text-only diff mode used by Aspell tests.
# Base diff lacks GNU -Z. Normalize trailing ASCII whitespace, retaining all
# other bytes and the real diff exit status. This is not a general diff replacement.
set -eu
[ "$#" = 4 ] && [ "$1" = -u ] && [ "$2" = -Z ] || exit 2
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-diff.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
LC_ALL=C /usr/bin/sed 's/[[:space:]]*$//' "$3" > "$work/expected"
LC_ALL=C /usr/bin/sed 's/[[:space:]]*$//' "$4" > "$work/actual"
result=0
/usr/bin/diff -u "$work/expected" "$work/actual" || result=$?
exit "$result"
