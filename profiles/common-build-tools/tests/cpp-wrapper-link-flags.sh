#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The cpp wrapper only preprocesses, but
# cwrappers takes arguments without -E for an executable link, so the MKPIE
# flags given to every wrapper reached clang-cpp, which warned "argument
# unused during compilation: '-pie'" on each run. The test sets up the
# wrappers of the target devel/glib2 in a new WRKOBJDIR: the cc wrapper
# keeps its MKPIE flags, the cpp wrapper has no link flags and preprocesses
# without a diagnostic.
# BMAKE runs the Ports bmake and keeps MAKECONF from the environment;
# MAKECONF selects a cross profile with MKPIE; the target dependencies of
# devel/glib2 are installed in the sysroot.
# Usage: cpp-wrapper-link-flags.sh BMAKE MAKECONF PKGSRC NEW_WORK
set -eu
[ "$#" = 4 ] || { echo 'Usage: cpp-wrapper-link-flags.sh BMAKE MAKECONF PKGSRC NEW_WORK' >&2; exit 2; }
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
(cd "$dir" && "$bmake" "$@" show-vars VARNAMES='CWRAPPERS_CONFIG_DIR PATH') \
    > "$work/vars" 2> "$work/vars.err" || fail "show-vars: $(cat "$work/vars.err")"
config=$(sed -n 1p "$work/vars")
path=$(sed -n 2p "$work/vars")
[ -n "$config" ] && [ -n "$path" ] || fail "empty variables: $(tr '\n' '|' < "$work/vars")"
(cd "$dir" && "$bmake" "$@" wrapper) > "$work/wrapper.log" 2>&1 ||
    fail "wrapper: $(tail -n 5 "$work/wrapper.log")"
grep -q '^append_executable=' "$config/cc" ||
    fail "the cc wrapper has no executable link flags; select a profile with MKPIE"
! grep '^append_\(executable\|shared\)=' "$config/cpp" > "$work/cpp-link-flags" ||
    fail "the cpp wrapper has link flags: $(tr '\n' ' ' < "$work/cpp-link-flags")"
printf 'int ember_cpp;\n' > "$work/plain.c"
env PATH="$path" CWRAPPERS_CONFIG_DIR="$config" cpp "$work/plain.c" \
    > "$work/plain.i" 2> "$work/plain.err" || fail "cpp: $(cat "$work/plain.err")"
[ ! -s "$work/plain.err" ] || fail "cpp printed a diagnostic: $(cat "$work/plain.err")"
grep -q 'ember_cpp' "$work/plain.i" || fail 'cpp did not preprocess the input'
echo 'PASS: the cpp wrapper preprocesses without link flags'
