#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The native Clang profile names an exact
# tool for every role, CPP included. pkgsrc reduces CC and CXX to their
# wrapper names but leaves CPP as it is, so an absolute clang-cpp ran past
# the cpp wrapper and its buildlink include transforms: the native
# devel/gobject-introspection build preprocesses glib/gi18n.h with $CPP
# (g-ir-scanner) and failed with "'libintl.h' file not found", because
# gettext-lib installs include/gettext/libintl.h, which only buildlink
# shows as libintl.h. The test sets up the wrappers of that package in a
# new WRKOBJDIR and preprocesses the same header with its CPP and PATH.
# BMAKE runs the Ports bmake and keeps MAKECONF from the environment;
# MAKECONF selects the native Clang profile; the native prefix has the
# dependencies of devel/gobject-introspection installed.
# Usage: native-cpp-wrapper.sh BMAKE MAKECONF PKGSRC NEW_WORK
set -eu
[ "$#" = 4 ] || { echo 'Usage: native-cpp-wrapper.sh BMAKE MAKECONF PKGSRC NEW_WORK' >&2; exit 2; }
bmake=$1 makeconf=$2 pkgsrc=$3 work=$4
for p in "$bmake" "$makeconf" "$pkgsrc" "$work"; do
    case "$p" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] || { echo "$work exists" >&2; exit 2; }
mkdir -p "$work/obj"
MAKECONF=$makeconf
export MAKECONF
dir=$pkgsrc/devel/gobject-introspection
set -- USE_CROSS_COMPILE=no WRKOBJDIR="$work/obj" \
    DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency
fail() { echo "FAIL: $*" >&2; exit 1; }
(cd "$dir" && "$bmake" "$@" show-vars VARNAMES='CPP LOCALBASE CWRAPPERS_CONFIG_DIR PATH') \
    > "$work/vars" 2> "$work/vars.err" || fail "show-vars: $(cat "$work/vars.err")"
cpp=$(sed -n 1p "$work/vars")
localbase=$(sed -n 2p "$work/vars")
config=$(sed -n 3p "$work/vars")
path=$(sed -n 4p "$work/vars")
[ -n "$cpp" ] && [ -n "$localbase" ] && [ -n "$config" ] && [ -n "$path" ] ||
    fail "empty variables: $(tr '\n' '|' < "$work/vars")"
(cd "$dir" && "$bmake" "$@" wrapper) > "$work/wrapper.log" 2>&1 ||
    fail "wrapper: $(tail -n 5 "$work/wrapper.log")"
printf '#include <glib/gi18n.h>\n' > "$work/gi18n.c"
set -f
set -- $cpp
set +f
env PATH="$path" CWRAPPERS_CONFIG_DIR="$config" "$@" -I"$localbase/include" \
    -I"$localbase/include/glib-2.0" -I"$localbase/lib/glib-2.0/include" "$work/gi18n.c" \
    > "$work/gi18n.i" 2> "$work/gi18n.err" ||
    fail "CPP=$cpp does not preprocess glib/gi18n.h: $(grep -m 1 error "$work/gi18n.err")"
grep -q '/\.buildlink/include/libintl\.h"' "$work/gi18n.i" ||
    fail "CPP=$cpp did not read libintl.h from the buildlink tree"
echo "PASS: native CPP ($cpp) runs through the cpp wrapper and buildlink"
