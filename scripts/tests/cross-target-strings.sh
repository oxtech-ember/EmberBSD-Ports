#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Cross builds create strings, by name and with the target prefix, from the
# selected SDK tool directory (x264 configure reads object endianness with it).
# Usage: cross-target-strings.sh BMAKE PREPARED_PKGSRC
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
q() { "$bmake" -f "$tree/mk/tools/cross.NetBSD.mk" TOOLDIR=/sdk/tools \
    MACHINE_GNU_PLATFORM=aarch64--netbsd PKGSRC_COMPILER=clang -V "\${$1}"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(q TOOLS_PATH.strings)" = /sdk/tools/bin/aarch64--netbsd-strings ] ||
    fail 'cross strings is not the SDK target strings'
[ "$(q TOOLS_PATH.aarch64--netbsd-strings)" = /sdk/tools/bin/aarch64--netbsd-strings ] ||
    fail 'cross prefixed strings is not the SDK target strings'
case " $(q TOOLS_CREATE) " in
*' strings '*) ;; *) fail 'strings is not created in the tools directory' ;;
esac
case " $(q TOOLS_CREATE) " in
*' aarch64--netbsd-strings '*) ;; *) fail 'aarch64--netbsd-strings is not created' ;;
esac
echo 'PASS: cross builds create strings and the prefixed strings from the SDK tools'
