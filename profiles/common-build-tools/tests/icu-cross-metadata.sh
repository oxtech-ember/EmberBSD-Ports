#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise actual ICU development metadata.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC MAKECONF ICU_WORK NEW_WORK" >&2; exit 2; }
pkgsrc=$1 conf=$2 icuwork=$3 work=$4
bmake=${BMAKE:-bmake}
mkdir "$work"
"$bmake" -C "$pkgsrc/textproc/icu" MAKECONF="$conf" show-vars \
    VARNAMES='CONFIG_SHELL CROSS_DESTDIR PKGVERSION_NOREV' > "$work/settings"
buildshell=$(sed -n '1p' "$work/settings")
sysroot=$(sed -n '2p' "$work/settings")
version=$(sed -n '3p' "$work/settings")
[ -n "$buildshell" ] && [ -n "$sysroot" ] && [ "$version" = 78.3 ]
mkdir -p "$work/dest/usr/pkg/bin" "$work/dest/usr/pkg/lib/icu/$version"
cp -p "$icuwork/icu/source/config/icu-config" "$work/dest/usr/pkg/bin/icu-config"
cp -p "$icuwork/icu/source/config/Makefile.inc" "$work/dest/usr/pkg/lib/icu/$version/Makefile.inc"
cp -p "$icuwork/icu/source/config/pkgdata.inc" "$work/dest/usr/pkg/lib/icu/$version/pkgdata.inc"
chmod u+w "$work/dest/usr/pkg/bin/icu-config" "$work/dest/usr/pkg/lib/icu/$version/"*
# This is the real failed build output, not a fabricated metadata fixture.
grep -Fq "$buildshell" "$work/dest/usr/pkg/bin/icu-config"
"$bmake" -C "$pkgsrc/textproc/icu" MAKECONF="$conf" DESTDIR="$work/dest" \
    ember-icu-cross-metadata > "$work/rewrite.log" 2>&1
file="$work/dest/usr/pkg/bin/icu-config"
[ "$(head -n 1 "$file")" = '#!/bin/sh' ]
[ "$("$buildshell" "$file" --noverify --version | sed 's/[[:space:]]*$//')" = "$version" ]
[ "$("$buildshell" "$file" --noverify --cc | sed 's/[[:space:]]*$//')" = /usr/pkg/gcc16/bin/gcc ]
[ "$("$buildshell" "$file" --noverify --cxx | sed 's/[[:space:]]*$//')" = '/usr/pkg/gcc16/bin/g++ -std=gnu++11' ]
for file in "$work/dest/usr/pkg/bin/icu-config" "$work/dest/usr/pkg/lib/icu/$version/Makefile.inc" "$work/dest/usr/pkg/lib/icu/$version/pkgdata.inc"; do
    if { [ "$buildshell" != /bin/sh ] && grep -F "$buildshell" "$file"; } || \
        grep -F "$sysroot" "$file" || \
        grep -E 'aarch64--netbsd-(gcc|g\+\+|ar|ranlib)|-o [^ ]+ -g ' "$file"; then
        echo 'Installed ICU metadata retains a build-host command' >&2; exit 1
    fi
    shasum -a 256 "$file"
done > "$work/rewritten.sha256"
"$bmake" -C "$pkgsrc/textproc/icu" MAKECONF="$conf" DESTDIR="$work/dest" \
    ember-icu-cross-metadata > "$work/repeat.log" 2>&1
shasum -a 256 -c "$work/rewritten.sha256" > "$work/idempotent.log"
"$bmake" -C "$pkgsrc/textproc/icu" MAKECONF="$conf" show-icu-cross-tools > "$work/native-tools.txt"
test -s "$work/native-tools.txt"
"$bmake" -C "$pkgsrc/textproc/icu" MAKECONF="$conf" \
    ICU_CROSS_DIR="$work/cross-tools" ICU_CROSS_COOKIE="$work/cross-tools/.cookie" \
    icu-cross-tools > "$work/cross-tools.log" 2>&1
grep -qx "CROSS_ICU_VERSION=$version" "$work/cross-tools/config/icucross.mk"
echo 'PASS: real ICU cross metadata, target shell/compiler settings, native release match and idempotent installation'
