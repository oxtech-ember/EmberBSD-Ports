#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
set -eu
cd "$(dirname "$0")"
while read -r expected library; do
    [ "$(sha256 -q "$library")" = "$expected" ]
done < libraries.sha256
: > conftest.1
: > conftest.2
timeout 15 ./constructor
[ ! -r conftest.1 ] && [ ! -r conftest.2 ]
printf 'PASS: upstream constructor/destructor runtime probe\n'
: > conftest.1
: > conftest.2
timeout 15 ./constructor-no-attributes
[ -r conftest.1 ] && [ -r conftest.2 ]
printf 'PASS: missing-attribute runtime negative control\n'
rm conftest.1 conftest.2
timeout 15 ./printf
printf 'PASS: upstream positional printf runtime probe\n'
KRB5_CONFIG="$PWD/krb5.conf" timeout 45 ./client
timeout 15 ./unload /usr/pkg/lib
ldd ./client
