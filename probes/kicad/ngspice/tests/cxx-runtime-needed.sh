#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu

if [ "$#" -ne 3 ]; then
	printf 'usage: %s READELF SHARED_LIBRARY EXPECTED_CXX_RUNTIME\n' "$0" >&2
	exit 2
fi

readelf=$1
library=$2
expected=$3
dynamic=$($readelf -d "$library")
actual=$(printf '%s\n' "$dynamic" | sed -n 's/.*(NEEDED).*\[\([^]]*\)\].*/\1/p' |
	grep -E '^(libc\+\+|libstdc\+\+)[.]so[.]' || true)
count=$(printf '%s\n' "$actual" | sed '/^$/d' | wc -l | tr -d ' ')

if [ "$count" -ne 1 ] || [ "$actual" != "$expected" ]; then
	printf 'FAIL: expected exactly %s, found: %s\n' "$expected" "$actual" >&2
	exit 1
fi

printf 'PASS: %s directly needs %s\n' "$library" "$expected"
