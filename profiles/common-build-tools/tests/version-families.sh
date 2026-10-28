#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The export keeps one version of each family.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 work=$2
bmake=${BMAKE:-bmake}
mkdir "$work"
for kept in lang/python315 lang/lua55 lang/gcc16-libs lang/go127 lang/php85 \
    lang/ruby40 lang/openjdk21 databases/postgresql18-client \
    databases/mariadb118-client security/openssl lang/tcl x11/tk print/poppler-qt6 \
    graphics/opencv graphics/opencv-contrib; do
    [ -d "$pkgsrc/$kept" ] || { echo "Missing kept $kept" >&2; exit 1; }
done
for old in lang/python314 lang/lua54 lang/gcc10-libs lang/go126 lang/php84 \
    lang/ruby34 lang/openjdk17 databases/postgresql17-client \
    databases/mariadb114-client databases/mysql80-client security/libressl \
    lang/tcl90 x11/tk90 print/poppler-qt5 local-robotics/opencv5 \
    graphics/opencv-contrib-face; do
    [ ! -e "$pkgsrc/$old" ] || { echo "Old version $old exported" >&2; exit 1; }
    if grep -Eq "^SUBDIR[+]?=[[:space:]]+${old#*/}\$" "$pkgsrc/${old%/*}/Makefile"; then
        echo "Old version $old listed in ${old%/*}/Makefile" >&2; exit 1
    fi
done
printf 'BSD_PKG_MK=\tyes\n.include "%s/EMBERBSD-DEFAULTS-MK.CONF"\nall:\n' "$pkgsrc" \
    > "$work/Makefile"
reason() {
    "$bmake" -f "$work/Makefile" PKGPATH="$1" -v PKG_FAIL_REASON
}
for old in lang/python314 lang/lua54 lang/gcc15 databases/postgresql17-client \
    databases/mysql80-client security/libressl lang/go126 lang/php84 lang/tcl90 \
    x11/tk90 print/poppler-qt5 local-robotics/opencv5 graphics/opencv-contrib-face; do
    reason "$old" | grep -Fq 'EmberBSD keeps only' ||
        { echo "Guard accepted $old" >&2; exit 1; }
done
for kept in lang/python315 lang/lua55 lang/gcc16-libs databases/postgresql18-server \
    databases/mariadb118-server net/wireshark lang/go127 lang/go-bin lang/php85 \
    lang/tcl x11/tk lang/tclx x11/tktable graphics/opencv graphics/opencv-contrib; do
    [ -z "$(reason "$kept")" ] || { echo "Guard rejected $kept" >&2; exit 1; }
done
# The exported version knobs default to and accept only the kept versions.
for knob in lang/lua/luaversion.mk:LUA_VERSION_DEFAULT:55 \
    lang/lua/luaversion.mk:LUA_VERSIONS_ACCEPTED:55 \
    lang/python/pyversion.mk:PYTHON_VERSIONS_ACCEPTED:315 \
    lang/nodejs/nodeversion.mk:NODE_VERSIONS_ACCEPTED:26; do
    file=${knob%%:*} rest=${knob#*:}
    grep -Eq "^${rest%%:*}[?]=[[:space:]]+${rest#*:}\$" "$pkgsrc/$file" ||
        { echo "$file does not offer only ${rest#*:} in ${rest%%:*}" >&2; exit 1; }
done
echo 'PASS: the export and the guard keep one version of each family.'
