#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that devel/gdb gives -std=gnu17 to the C compiler only. With
# CFLAGS+=-std=gnu17 the top-level configure copied the flag into
# CXXFLAGS, clang++ rejected it ("invalid argument '-std=gnu17' not
# allowed with 'C++'"), and gdbsupport's configure stopped with "A
# compiler with support for C++17 language features is required".
#
# Usage: BMAKE=bmake c-std-flags.sh PKGSRC MAKECONF

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

v() {
	MAKECONF=$makeconf "$bmake" -C "$pkgsrc/devel/gdb" \
	    MAKECONF="$makeconf" -V "$1"
}
fail=0
case " $(v '${CFLAGS}') $(v '${CXXFLAGS}') " in
*" -std=gnu17 "*) echo "FAIL: -std=gnu17 is in CFLAGS or CXXFLAGS"; fail=1 ;;
esac
case " $(v '${CWRAPPERS_APPEND.cc}') " in
*" -std=gnu17 "*) ;;
*) echo "FAIL: the C compiler wrapper does not add -std=gnu17"; fail=1 ;;
esac
case " $(v '${CWRAPPERS_APPEND.cxx}') " in
*" -std=gnu17 "*) echo "FAIL: the C++ compiler wrapper adds -std=gnu17"; fail=1 ;;
esac
[ $fail -eq 0 ] || exit 1
echo "PASS: only the C compiler gets -std=gnu17"
