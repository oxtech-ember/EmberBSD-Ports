#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that the Darwin post-build commands of lang/tcl use the selected
# install-name tool and otool instead of whatever is first in PATH.
# A native macOS build without Xcode's command line tools in PATH failed
# with "exec(install_name_tool): No such file or directory".
#
# Usage: BMAKE=bmake darwin-tools.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a NetBSD cross build on macOS; the native
# recipe is checked with USE_CROSS_COMPILE=no and a dry run (-n).

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}
dir=$pkgsrc/lang/tcl

query() {
	MAKECONF=$makeconf "$bmake" -C "$dir" MAKECONF="$makeconf" \
	    USE_CROSS_COMPILE=no -V "\${$1}"
}

[ "$(query OPSYS)" = Darwin ] || { echo "SKIP: not a macOS host"; exit 0; }
int=$(query EMBERBSD_DARWIN_INSTALL_NAME_TOOL)
otool=$(query MACHO_OTOOL)
case $int in /*) ;; *) echo "FAIL: no absolute install-name tool selected: '$int'"; exit 1;; esac
case $otool in /*) ;; *) echo "FAIL: no absolute otool selected: '$otool'"; exit 1;; esac

out=$(MAKECONF=$makeconf "$bmake" -C "$dir" MAKECONF="$makeconf" \
    USE_CROSS_COMPILE=no -n post-build)

ids=$(printf '%s\n' "$out" | grep -c -- ' -id ' || :)
selected=$(printf '%s\n' "$out" | grep -c -F -- "$int -id " || :)
if [ "$ids" -ne 6 ] || [ "$selected" -ne 6 ]; then
	echo "FAIL: $selected of $ids install-name commands use $int (expected 6 of 6)"
	printf '%s\n' "$out" | grep -- ' -id ' | sed 's/^/  /'
	exit 1
fi
if ! printf '%s\n' "$out" | grep -q -F -- "\$($otool -D "; then
	echo "FAIL: the thread library identity is not read with $otool"
	printf '%s\n' "$out" | grep -- ' -D ' | sed 's/^/  /'
	exit 1
fi
echo "PASS: tcl post-build uses $int and $otool"
