#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the prepared cross-profile helper.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 PREPARED_PKGSRC" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exported=$(CDPATH= cd -- "$1" && pwd)
[ -f "$exported/EMBERBSD-CROSS-MK.CONF" ]
[ -x "$exported/sort-c.sh" ] || { echo 'Missing exported cross sort helper.' >&2; exit 1; }
cmp "$root/profiles/common-build-tools/cross/sort-c.sh" "$exported/sort-c.sh"
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-export-sort.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
cat > "$work/check.mk" <<MAKE
BSD_PKG_MK=yes
PKGPATH=devel/zlib
NATIVE_OPSYS=Darwin
USE_CROSS_COMPILE=yes
EMBERBSD_CROSS_TOOLS=$exported
EMBERBSD_CROSS_SYSROOT=$exported
EMBERBSD_CROSS_HOST_PREFIX=$exported
.include "$exported/EMBERBSD-CROSS-MK.CONF"
MAKE
selected=$("${BMAKE:-bmake}" -f "$work/check.mk" -V TOOLS_PLATFORM.sort)
[ "$selected" = "$exported/sort-c.sh" ]
printf 'a\n_\nZ\n' | LC_ALL=en_US.UTF-8 "$selected" > "$work/actual"
printf 'Z\n_\na\n' > "$work/expected"
cmp "$work/expected" "$work/actual"
echo 'PASS: exported cross profile executes its matching C-locale sort helper'
