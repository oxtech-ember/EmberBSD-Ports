#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); lang/flang-rt refuses a Flang of another
# LLVM release, because the runtime and its modules belong to one Flang.
# The selected profile pins EMBERBSD_FLANG, so the test moves the package's
# LLVM release instead: the same driver must then be refused.
# Usage: BMAKE=BMAKE flang-version.sh EXPORTED_PKGSRC NEW_WORK
set -eu
[ "$#" -eq 2 ] || { echo "Usage: BMAKE=BMAKE $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
make=${BMAKE:?set BMAKE to the selected bmake}
fail() { echo "FAIL: $*" >&2; exit 1; }
query() { "$make" -C "$pkgsrc/lang/flang-rt" WRKOBJDIR="$work/obj" "$@" \
    -V '${PKG_FAIL_REASON}' -V '${LLVM_MAJOR_VERSION}' -V '${EMBERBSD_FLANG}'; }
query > "$work/same" || fail "cannot query lang/flang-rt"
major=$(sed -n 2p "$work/same")
flang=$(sed -n 3p "$work/same")
case $flang in /*) ;; *) fail "the profile selects no Flang driver";; esac
case $(sed -n 1p "$work/same") in
*EMBERBSD_FLANG*) fail "the matching Flang is refused: $(sed -n 1p "$work/same")";;
esac
version=$("$flang" --version | sed -n '1s/^[^ ]* version \([^ ]*\).*/\1/p')
[ "${version%%.*}" = "$major" ] || fail "the selected Flang $version is not LLVM $major"
other=$((major + 1))
query LLVM_VERSION="$other.1.0" > "$work/other" || fail "cannot query lang/flang-rt"
grep -qF "EMBERBSD_FLANG is Flang $version, not LLVM $other" "$work/other" ||
    fail "Flang $version is accepted for LLVM $other"
echo "PASS: lang/flang-rt accepts Flang $version for LLVM $major and refuses it for LLVM $other"
