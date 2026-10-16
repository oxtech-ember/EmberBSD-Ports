#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Prepare the same audited original GCC sources as the cross frontend recipe.
set -eu
[ "$#" -eq 3 ] || { echo 'Usage: prepare-source.sh EXPORTED_PKGSRC GCC_ARCHIVE NEW_SOURCE' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
profile=$(CDPATH= cd -- "$here/.." && pwd -P)
recipe=$1/lang/gcc16 archive=$2 source=$3
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths without whitespace.' >&2; exit 2;; esac
done
[ ! -e "$source" ] && [ ! -L "$source" ] || { echo 'NEW_SOURCE already exists.' >&2; exit 2; }
. "$here/audit-source.sh"
mkdir "$source"
tar -xf "$archive" --strip-components=1 -C "$source"
for name in $patches; do
    # Audited above, omitted for the same reason as cross/build.sh.
    [ "$name" != patch-gcc_Makefile.in ] || continue
    patch -f -N -F 0 -p0 -d "$source" < "$recipe/patches/$name"
done
configure=$source/libstdc++-v3/configure
[ "$(grep -c '^libtool_VERSION=6:' "$configure")" -eq 1 ] || {
    echo 'Unexpected upstream libstdc++ ABI selection.' >&2; exit 1;
}
# Preserve executable mode, including when configure is generated upstream.
sed 's,libtool_VERSION=6:,libtool_VERSION=7:,g' "$configure" > "$source/libstdc-configure.tmp"
cat "$source/libstdc-configure.tmp" > "$configure"
rm "$source/libstdc-configure.tmp"
