#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). EMBERBSD-DEFAULTS-MK.CONF keeps its Darwin
# native block (MACHO_USE_LOAD_COMMANDS, PKG_OPTIONS.graphviz -gd) to
# native builds. The cross profile includes it while OPSYS is still the
# build host's Darwin, and a target build has no USE_CROSS_COMPILE on the
# command line, so the cross profile must select its cross default before
# that include. A native build (USE_CROSS_COMPILE=no) keeps the block.
# The fixture stubs the native inputs and the prepared target tools.
# Usage: cross-darwin-native-defaults.sh BMAKE NEW_DIRECTORY
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-darwin-native-defaults.sh BMAKE NEW_DIRECTORY' >&2; exit 2; }
bmake=$1 work=$2
case "$bmake$work" in *[!A-Za-z0-9_./+-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
case "$work" in /*) ;; *) echo 'NEW_DIRECTORY must be absolute' >&2; exit 2 ;; esac
[ ! -e "$work" ] || { echo "$work exists" >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
mkdir -p "$work/profile" "$work/tools" "$work/sysroot" "$work/host"
cp "$ports/profiles/common-build-tools/cross/mk.conf" "$work/profile/mk.conf"
cp "$ports/pkgsrc/defaults.mk.conf" "$work/profile/EMBERBSD-DEFAULTS-MK.CONF"
cp "$ports/pkgsrc/versions.mk" "$work/profile/EMBERBSD-VERSIONS.MK"
: > "$work/profile/native-tools.mk"
# The native profile of the host prefix, included by native builds.
: > "$work/mk.conf"
cat > "$work/tools/target.mk" <<'EOF'
_EMBER_TARGET_FAMILY=clang
_EMBER_TARGET_TARGET=aarch64
_EMBER_TARGET_TRIPLET=${_EMBER_CROSS_TRIPLET}
_EMBER_TARGET_SYSROOT=${CROSS_DESTDIR}
_EMBER_TARGET_TOOLS=${TOOLDIR}
PKGSRC_COMPILER=clang
CLANGBASE=${TOOLDIR}
EOF
cat > "$work/Makefile" <<EOF
BSD_PKG_MK=yes
OPSYS=Darwin
EMBERBSD_CROSS_TOOLS=$work/tools
EMBERBSD_CROSS_SYSROOT=$work/sysroot
EMBERBSD_CROSS_HOST_PREFIX=$work/host
.include "$work/profile/mk.conf"
EOF
fail() { echo "FAIL: $*" >&2; exit 1; }
read_vars() { "$bmake" -f "$work/Makefile" "$@" -v USE_CROSS_COMPILE -v MACHO_USE_LOAD_COMMANDS -v PKG_OPTIONS.graphviz | tr '\n' ' '; }
target=$(read_vars) || fail "the target parse failed: $target"
[ "$target" = 'yes   ' ] || fail "a target build takes the Darwin native defaults (USE_CROSS_COMPILE MACHO_USE_LOAD_COMMANDS PKG_OPTIONS.graphviz: $target)"
native=$(read_vars USE_CROSS_COMPILE=no) || fail "the native parse failed: $native"
[ "$native" = 'no yes -gd ' ] || fail "a native build lost the Darwin native defaults: $native"
echo 'PASS: the Darwin native defaults apply to native builds of the cross profile, not to target builds'
