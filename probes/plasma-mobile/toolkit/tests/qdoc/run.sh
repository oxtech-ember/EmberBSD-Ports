#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real Clang-backed documentation generation.
set -eu
[ "$#" = 2 ] || { echo 'Usage: qdoc/run.sh QDOC NEW_OUTPUT' >&2; exit 2; }
qdoc=$1
case "$qdoc:$2" in /*:/*) ;; *) exit 2;; esac
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
"$qdoc" --version > "$work/version.txt"
grep -Fxq 'qdoc 6.12.0' "$work/version.txt"
cp "$source/probe.h" "$source/probe.cpp" "$source/probe.qdocconf" "$work/"
(cd "$work" && "$qdoc" --outputdir "$work/html" probe.qdocconf) > "$work/qdoc.log" 2>&1
grep -q 'Provides a documented C++ answer' "$work/html/probe.html"
grep -q 'Returns the value 42' "$work/html/probe.html"
grep -q 'answer' "$work/html/emberqdocprobe.index"
# A missing configuration must fail, not reuse the previous generated output.
if "$qdoc" --outputdir "$work/invalid" "$work/missing.qdocconf" > "$work/missing.log" 2>&1; then
    echo 'Missing configuration accepted' >&2; exit 1
fi
[ ! -f "$work/invalid/probe.html" ]
echo 'PASS: Clang-backed C++ class/member documentation and missing-input rejection'
