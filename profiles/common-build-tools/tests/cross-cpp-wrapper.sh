#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). pkgsrc reduces CC and CXX to the names of
# their cwrappers but leaves CPP as it is. The Clang cross profile named
# the absolute target clang-cpp, which ran past the cpp wrapper and its
# buildlink include transforms: preprocessing <pcre2.h> for the target
# devel/glib2 failed with "'pcre2.h' file not found", although the cc
# wrapper finds it in the buildlink tree. The test sets up the wrappers of
# that package in a new WRKOBJDIR and preprocesses the header with its CPP
# and PATH for the target, then requires that CPP is a wrapper.
# BMAKE runs the Ports bmake and keeps MAKECONF from the environment;
# MAKECONF selects the Clang cross profile for an AArch64 NetBSD target;
# the target dependencies of devel/glib2 are installed in the sysroot.
# Usage: cross-cpp-wrapper.sh BMAKE MAKECONF PKGSRC NEW_WORK
set -eu
[ "$#" = 4 ] || { echo 'Usage: cross-cpp-wrapper.sh BMAKE MAKECONF PKGSRC NEW_WORK' >&2; exit 2; }
bmake=$1 makeconf=$2 pkgsrc=$3 work=$4
for p in "$bmake" "$makeconf" "$pkgsrc" "$work"; do
    case "$p" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] || { echo "$work exists" >&2; exit 2; }
mkdir -p "$work/obj"
MAKECONF=$makeconf
export MAKECONF
dir=$pkgsrc/devel/glib2
set -- WRKOBJDIR="$work/obj" DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency
fail() { echo "FAIL: $*" >&2; exit 1; }
(cd "$dir" && "$bmake" "$@" show-vars \
    VARNAMES='USE_CROSS_COMPILE CPP CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR PATH') \
    > "$work/vars" 2> "$work/vars.err" || fail "show-vars: $(cat "$work/vars.err")"
cross=$(sed -n 1p "$work/vars")
cpp=$(sed -n 2p "$work/vars")
config=$(sed -n 3p "$work/vars")
bindir=$(sed -n 4p "$work/vars")
path=$(sed -n 5p "$work/vars")
[ "$cross" = yes ] || fail "USE_CROSS_COMPILE is '$cross'; select the cross profile"
[ -n "$cpp" ] && [ -n "$config" ] && [ -n "$bindir" ] && [ -n "$path" ] ||
    fail "empty variables: $(tr '\n' '|' < "$work/vars")"
(cd "$dir" && "$bmake" "$@" wrapper) > "$work/wrapper.log" 2>&1 ||
    fail "wrapper: $(tail -n 5 "$work/wrapper.log")"
cat > "$work/pcre2.c" <<'SRC'
#if !defined(__aarch64__) || !defined(__NetBSD__)
#error not preprocessed for the AArch64 NetBSD target
#endif
#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
SRC
set -f
set -- $cpp
set +f
env PATH="$path" CWRAPPERS_CONFIG_DIR="$config" "$@" "$work/pcre2.c" \
    > "$work/pcre2.i" 2> "$work/pcre2.err" ||
    fail "CPP=$cpp does not preprocess pcre2.h: $(grep -m 1 error "$work/pcre2.err")"
grep -q '/\.buildlink/include/pcre2\.h"' "$work/pcre2.i" ||
    fail "CPP=$cpp did not read pcre2.h from the buildlink tree"
[ ! -s "$work/pcre2.err" ] || fail "CPP=$cpp printed a diagnostic: $(cat "$work/pcre2.err")"
found=$(env PATH="$path" sh -c 'command -v "$1"' sh "$1") || fail "CPP=$cpp is not in PATH"
[ "$found" = "$bindir/${1##*/}" ] || fail "CPP=$cpp runs $found, not a wrapper in $bindir"
echo "PASS: cross CPP ($cpp) runs through the cpp wrapper and buildlink"
