#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apr-cross-configure.sh PKGSRC MAKECONF
#
# apr's configure runs test programs and checks for /dev/zero, which stops
# a cross build with "cannot check for file existence when cross compiling".
# Configure the recipe (libuuid must be installed) and compare the results
# with the apr-1.7.6 package built natively on NetBSD 11.0 aarch64.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/devel/apr makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
[ "$(bm -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: the expected results are for a NetBSD target" >&2; exit 2; }
src=$(bm -V '${WRKSRC}')
trap 'bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
log=$(mktemp)
bm configure >"$log" 2>&1 || {
	echo "FAIL: configure: $(grep 'configure: error' "$log" | head -1)"
	rm -f "$log"; exit 1; }
rm -f "$log"
failures=0
expect() {
	file=$1; shift
	for line in "$@"; do
		grep -Eq "^$line\$" "$src/$file" || {
			echo "FAIL: $file lacks '$line'"; failures=$((failures + 1)); }
	done
}
expect include/apr.h \
	'#define APR_HAVE_SHMEM_MMAP_ZERO +1' \
	'#define APR_HAS_POSIXSEM_SERIALIZE +1' \
	'#define APR_HAS_PROC_PTHREAD_SERIALIZE +0' \
	'#define APR_HAVE_SETRLIMIT +1' \
	'#define APR_HAS_THREADS +1' \
	'#define APR_O_NONBLOCK_INHERITED +1'
expect include/arch/unix/apr_private.h \
	'#define HAVE_ACCEPT4 1' \
	'#define HAVE_ATOMIC_BUILTINS 1' \
	'#define HAVE_ATOMIC_BUILTINS64 1' \
	'#define HAVE_DUP3 1' \
	'#define HAVE_GAI_ADDRCONFIG 1' \
	'#define HAVE_SOCK_CLOEXEC 1' \
	'#define STRERROR_R_RC_INT 1'
expect build/apr_rules.mk \
	'EXTRA_CFLAGS= -pthread' \
	'EXTRA_LIBS=-lrt -lm -lcrypt +-lpthread'
[ "$failures" = 0 ] || exit 1
echo "PASS: apr configures like a native NetBSD build when cross compiling"
