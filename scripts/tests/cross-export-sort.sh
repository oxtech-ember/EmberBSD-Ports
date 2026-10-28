#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the exported profile with a selected prefix.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PREPARED_PKGSRC CROSS_MAKECONF" >&2; exit 2; }
exported=$(CDPATH= cd -- "$1" && pwd)
config=$2
[ -f "$exported/EMBERBSD-CROSS-MK.CONF" ]
[ -f "$config" ]
selected=$(MAKECONF="$config" "${BMAKE:-bmake}" -C "$exported/devel/pkgconf" -V '${TOOLS_PLATFORM.sort}')
prefix=$(MAKECONF="$config" "${BMAKE:-bmake}" -C "$exported/devel/pkgconf" -V '${EMBERBSD_HOST_PREFIX}')
[ "$selected" = "$prefix/bin/gsort" ]
[ -x "$selected" ]
locale=$(MAKECONF="$config" "${BMAKE:-bmake}" -C "$exported/devel/pkgconf" -V '${LC_ALL}')
[ "$locale" = C ]
actual=$(printf 'a\n_\nZ\n' | LC_ALL="$locale" "$selected")
[ "$actual" = "$(printf 'Z\n_\na\n')" ]
# Actual PLIST/libtool expansion and a child environment are tested by cross-sort.rb.
echo 'PASS: exported profile selects prefix gsort and C locale'
