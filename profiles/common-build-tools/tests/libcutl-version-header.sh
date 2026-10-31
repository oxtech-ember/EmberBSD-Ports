#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake libcutl-version-header.sh PKGSRC MAKECONF TARGET_CXX CXX_INCLUDE NEW_WORK
#
# libcutl compiles with -I$(top_srcdir), and its source root has a file
# named "version". libc++ headers include <version>, so the build read that
# file as C++ and stopped with "../version:1:1: error: expected
# unqualified-id". Extract the distfile, run the recipe's post-extract and
# Makefile.in SUBST edits, and compile a translation unit that includes a
# libc++ header with the same include path.
set -eu
[ "$#" -eq 5 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CXX CXX_INCLUDE NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cxx=$3 cxxinc=$4
case "$5" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$5"
work=$5
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/devel/libcutl" \
	    MAKECONF="$makeconf" WRKDIR="$work/package" WRKOBJDIR="$work/objects" \
	    _PKGSRC_BARRIER=yes "$@" </dev/null
}
mkdir "$work/package"
tar -xjf "$(bm -V '${DISTDIR}/${DISTFILES}')" -C "$work/package"
src=$(bm -V '${WRKSRC}')
bm post-extract > "$work/post-extract.log" 2>&1 ||
	{ echo "FAIL: post-extract: $(tail -1 "$work/post-extract.log")"; exit 1; }
for class in $(bm -V '${SUBST_CLASSES}'); do
	for file in $(bm -V "\${SUBST_FILES.$class}"); do
		eval "set -- $(bm -V "\${SUBST_SED.$class}")"
		sed "$@" "$src/$file" > "$work/subst" && mv "$work/subst" "$src/$file"
	done
done
for doc in $(sed -n 's/^dist_doc_DATA = //p' "$src/Makefile.in"); do
	[ -f "$src/$doc" ] || { echo "FAIL: Makefile.in installs the missing doc file $doc"; exit 1; }
done
printf '#include <exception>\nint main() { return 0; }\n' > "$work/probe.cxx"
(cd "$src/cutl" && "$cxx" -std=c++11 -nostdinc++ -isystem "$cxxinc" -I.. \
    -fsyntax-only "$work/probe.cxx" > "$work/compile.log" 2>&1) ||
	{ echo "FAIL: <exception> with -I\$(top_srcdir): $(grep -m1 error: "$work/compile.log")"; exit 1; }
echo "PASS: the libcutl source root does not shadow the C++ standard headers"
