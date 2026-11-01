#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Read the exported OpenSSL configure environment; do not build OpenSSL.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
fail() { echo "FAIL: $*" >&2; exit 1; }
ranlib_env() {
    "$bmake" -C "$tree/security/openssl" MAKECONF=/dev/null \
        PKG_ADMIN=/usr/bin/true PKG_INFO=/usr/bin/true PKGVULNDIR=/unused \
        "$@" -V '${CONFIGURE_ENV:MRANLIB=*}'
}
if [ "$(uname -s)" = Darwin ]; then
    # The darwin64 Configure targets otherwise run the cctools "ranlib -c".
    [ "$(ranlib_env TOOLS_PATH.ranlib=/native/bin/llvm-ranlib)" = RANLIB=ranlib ] ||
        fail 'native Darwin OpenSSL keeps the cctools ranlib option with llvm-ranlib'
fi
[ -z "$(ranlib_env TOOLS_PATH.ranlib=/usr/bin/ranlib)" ] ||
    fail 'OpenSSL replaces the Configure ranlib for another ranlib'
[ -z "$(ranlib_env)" ] || fail 'OpenSSL replaces the Configure ranlib without a selected ranlib'
echo 'PASS: native Darwin OpenSSL uses the selected llvm-ranlib without the cctools -c option'
