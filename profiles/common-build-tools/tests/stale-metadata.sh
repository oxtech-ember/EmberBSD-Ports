#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), stale PLIST and package metadata.
# Input PKGSRC must not contain pkgsrc-stale-metadata.patch yet.
# This test copies three pkgsrc fragments. It does not build packages.
set -eu

[ "$#" = 2 ] || {
    echo "Usage: $0 PKGSRC NEW_WORK" >&2
    exit 2
}
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bmake=${BMAKE:-bmake}
patch=${PATCH:-patch}
command -v "$bmake" >/dev/null 2>&1 || {
    echo 'A BSD make executable is required. Set BMAKE.' >&2
    exit 2
}
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
export LC_ALL=C

fail()
{
    echo "$*" >&2
    exit 1
}

for variant in original patched; do
    mkdir -p "$work/$variant/mk/install" "$work/$variant/mk/check" \
        "$work/$variant/mk/pkgformat/pkg"
    cp "$pkgsrc/mk/install/install.mk" "$work/$variant/mk/install/"
    cp "$pkgsrc/mk/check/check-shlibs-elf.awk" "$work/$variant/mk/check/"
    cp "$pkgsrc/mk/pkgformat/pkg/metadata.mk" "$work/$variant/mk/pkgformat/pkg/"
done
[ ! -e "$pkgsrc/mk/pkgformat/pkg/check-provides.sh" ] || fail 'Input already has the patch'
(cd "$work/patched" && "$patch" -F0 -p1 \
    < "$profile/patches/pkgsrc-stale-metadata.patch") > "$work/patch.log" 2>&1

# 1. Each install removes the PLIST and metadata before the PLIST target.
cat > "$work/order.mk" <<'EOF'
_PKGSRC_USE_CTF= no
CHECK_FILES= no
WRKSRC= /work
INSTALL_DIRS= /work
.include "${FRAGMENTS}/mk/install/install.mk"
EOF
order()
{
    "$bmake" -r -f "$work/order.mk" FRAGMENTS="$work/$1" -V _INSTALL_ALL_TARGETS |
        tr ' ' '\n' | awk 'NF { print }'
}
order original > "$work/order-original.txt"
order patched > "$work/order-patched.txt"
! grep -Fx plist-clean "$work/order-original.txt" >/dev/null ||
    fail 'Original install already cleans the PLIST'
position()
{
    awk -v name="$2" '$0 == name { print NR; exit }' "$1"
}
clean=$(position "$work/order-patched.txt" plist-clean)
metadata=$(position "$work/order-patched.txt" _pkgformat-clean-metadata)
plist=$(position "$work/order-patched.txt" plist)
generate=$(position "$work/order-patched.txt" _pkgformat-generate-metadata)
[ -n "$clean" ] && [ -n "$metadata" ] && [ -n "$plist" ] && [ -n "$generate" ] ||
    fail 'Missing install target'
[ "$clean" -lt "$plist" ] && [ "$metadata" -lt "$plist" ] && [ "$plist" -lt "$generate" ] ||
    fail 'Records are not removed before they are generated'

# 2. The cross ELF check does not take a listed object from the sysroot.
dest=$work/dest
sysroot=$work/sysroot
mkdir -p "$dest/usr/pkg/lib" "$sysroot/usr/pkg/lib" "$work/bin"
printf '\177ELF' > "$sysroot/usr/pkg/lib/libstale.so.7"
printf '\177ELF' > "$dest/usr/pkg/lib/libcurrent.so.8"
cat > "$work/bin/readelf" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$work/bin/readelf"
elf_check()
{
    : > "$work/requires"
    printf '%s\n' "$2" | DESTDIR="$dest" CROSS_DESTDIR="$sysroot" \
        REQUIRES_FILE="$work/requires" READELF="$work/bin/readelf" \
        PLATFORM_RPATH=/usr/lib WRKDIR="$work" \
        awk -f "$work/$1/mk/check/check-shlibs-elf.awk"
}
[ -z "$(elf_check original "$dest/usr/pkg/lib/libstale.so.7")" ] ||
    fail 'Original check did not reproduce the sysroot fallback'
elf_check patched "$dest/usr/pkg/lib/libstale.so.7" > "$work/elf-stale.txt"
grep -F 'libstale.so.7: not installed in DESTDIR' "$work/elf-stale.txt" >/dev/null ||
    fail 'Patched check accepted an object from the sysroot'
for variant in original patched; do
    [ -z "$(elf_check "$variant" "$dest/usr/pkg/lib/libcurrent.so.8")" ] ||
        fail "$variant check rejected an installed object"
done

# 3. Each PROVIDES entry is in the PLIST and in DESTDIR.
helper=$work/patched/mk/pkgformat/pkg/check-provides.sh
printf '%s\n' lib/libcurrent.so.8 lib/libmissing.so.8 > "$work/PLIST"
provides()
{
    printf '%s\n' "$@" > "$work/BUILD_INFO"
    sh "$helper" "$dest" /usr/pkg "$work/PLIST" "$work/BUILD_INFO" 2> "$work/provides.err"
}
provides 'PKGPATH=x11/example' 'PROVIDES=/usr/pkg/lib/libcurrent.so.8' ||
    fail 'Valid PROVIDES entry failed'
if provides 'PROVIDES=/usr/pkg/lib/libstale.so.7'; then fail 'Stale PROVIDES entry passed'; fi
grep -F 'is not in the PLIST' "$work/provides.err" >/dev/null
if provides 'PROVIDES=/usr/pkg/lib/libmissing.so.8'; then fail 'Missing PROVIDES file passed'; fi
grep -F 'is not installed in DESTDIR' "$work/provides.err" >/dev/null
if provides 'PROVIDES=/opt/lib/libcurrent.so.8'; then fail 'Outside PROVIDES entry passed'; fi
grep -F 'check-provides.sh' "$work/patched/mk/pkgformat/pkg/metadata.mk" >/dev/null ||
    fail 'Metadata generation does not run the PROVIDES check'

echo 'PASS: install order, sysroot fallback reproduced and rejected, four PROVIDES cases'
