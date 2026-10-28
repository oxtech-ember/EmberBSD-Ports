#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Patched consumers depend on the kept versions.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 EXPORTED_PKGSRC" >&2; exit 2; }
pkgsrc=$1
bmake=${BMAKE:-bmake}
fail=0
while read -r pkgpath expected; do
    deps=$("$bmake" -C "$pkgsrc/$pkgpath" show-depends-pkgpaths) ||
        { echo "Cannot query $pkgpath" >&2; exit 1; }
    for dep in $expected; do
        printf '%s\n' "$deps" | grep -Fqx "$dep" ||
            { echo "$pkgpath does not depend on $dep" >&2; fail=1; }
    done
    for dep in $deps; do
        [ -f "$pkgsrc/$dep/Makefile" ] ||
            { echo "$pkgpath depends on missing $dep" >&2; fail=1; }
    done
done <<'LIST'
devel/Guitar lang/ruby40
devel/SDL2 devel/SDL3
devel/git-gitk x11/tk
devel/hexpatch lang/lua55
devel/umbrello x11/qt6-qtbase devel/kf6-ktexteditor
editors/mle lang/lua55
editors/xournalpp lang/lua55
emulators/flycast lang/lua55
games/etlegacy lang/lua55
games/etlegacy-server lang/lua55
games/powder-toy lang/lua55
games/simgear graphics/osg
graphics/darktable lang/lua55
graphics/osg lang/lua55
lang/hs-lua lang/lua55
multimedia/vlc lang/lua55
net/grilo-plugins lang/lua55
net/ntopng lang/lua55
net/qrcp lang/go127
security/zoneminder multimedia/ffmpeg9 devel/pcre2 databases/mariadb118-client
sysutils/vifm lang/lua55
sysutils/yazi lang/lua55
LIST
[ "$fail" = 0 ]
echo 'PASS: patched consumers depend on the kept versions.'
