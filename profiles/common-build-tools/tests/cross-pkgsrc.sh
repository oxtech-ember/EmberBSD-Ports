#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc platform/recursion/ELF regressions.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 EXPORTED_PKGSRC MAKECONF STAGED_PKGCONF NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
pkgsrc=$1 makeconf=$2 stage=$3 work=$4
bmake=${BMAKE:-bmake}
for path in "$pkgsrc" "$makeconf" "$stage" "$work"; do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
done
mkdir "$work"
cat > "$work/platform.mk" <<'MAKE'
OPSYS_VERSION=110000
OBJECT_FMT=ELF
USE_CROSS_COMPILE=yes
MACHINE_ARCH?=aarch64
.include "${PLATFORM_MK}"
MAKE
if "$bmake" -r -f "$work/platform.mk" PLATFORM_MK="$root/upstream/pkgsrc/mk/platform/NetBSD.mk" \
    -v _WRAP_EXTRA_ARGS.LD > "$work/platform-before.txt" 2>&1; then
    echo 'FAIL: pristine platform unexpectedly accepts an absent host architecture' >&2; exit 1
fi
"$bmake" -r -f "$work/platform.mk" PLATFORM_MK="$pkgsrc/mk/platform/NetBSD.mk" \
    -v _WRAP_EXTRA_ARGS.LD > "$work/platform-after.txt"
[ ! -s "$work/platform-after.txt" ] || [ -z "$(cat "$work/platform-after.txt")" ]
for host in i386 x86_64; do
    "$bmake" -r -f "$work/platform.mk" PLATFORM_MK="$pkgsrc/mk/platform/NetBSD.mk" \
        MACHINE_ARCH=i386 HOST_MACHINE_ARCH="$host" -v _WRAP_EXTRA_ARGS.LD > "$work/platform-$host.txt"
done
[ -z "$(cat "$work/platform-i386.txt")" ]
[ "$(cat "$work/platform-x86_64.txt")" = '-m elf_i386' ]
echo 'PASS: cross-platform parse and unchanged native i386 linker emulation'
cat > "$work/recursion.mk" <<'MAKE'
.PHONY: ember-host-before ember-host-after
ember-host-before:
	@cd ../../sysutils/checkperms && unset MAKEFLAGS && \
	 ${PKGSRC_SETENV} ${PKGSRC_MAKE_ENV} USE_CROSS_COMPILE=no \
	 ${MAKE} ${MAKEFLAGS} show-vars VARNAMES='OPSYS OS_VERSION PKGSRC_COMPILER LDFLAGS'
ember-host-after:
	@cd ../../sysutils/checkperms && unset MAKEFLAGS && \
	 ${PKGSRC_SETENV} ${PKGSRC_MAKE_ENV} USE_CROSS_COMPILE=no \
	 ${MAKE} ${_DEPENDS_MAKEFLAGS} show-vars VARNAMES='OPSYS OS_VERSION PKGSRC_COMPILER LDFLAGS'
MAKE
[ "$(uname -s)" = Darwin ] || { echo 'This cross-host regression currently requires macOS.' >&2; exit 2; }
for phase in before after; do
    "$bmake" -C "$pkgsrc/devel/pkgconf" MAKECONF="$makeconf" \
        -f Makefile -f "$work/recursion.mk" "ember-host-$phase" > "$work/recursion-$phase.txt"
done
[ "$(sed -n '1p' "$work/recursion-before.txt")" = NetBSD ]
[ "$(sed -n '1p' "$work/recursion-after.txt")" = Darwin ]
if grep -q -- '-zrelro' "$work/recursion-after.txt"; then echo "Unexpected matching output" >&2; exit 1; fi
echo 'PASS: native dependency recursion drops target-only platform values'
sysroot=$("$bmake" -C "$pkgsrc/devel/pkgconf" MAKECONF="$makeconf" -v CROSS_DESTDIR)
readelf=$("$bmake" -C "$pkgsrc/devel/pkgconf" MAKECONF="$makeconf" -v TOOLS_PATH.readelf)
export CROSS_DESTDIR="$sysroot" DESTDIR="$stage" PLATFORM_RPATH=/usr/lib READELF="$readelf"
export WRKDIR="$work" PKG_INFO_CMD=true DEPENDS_FILE=/dev/null
: > "$work/empty-plist"
export PREFIX=/usr/pkg PACKAGE_PLIST="$work/empty-plist"
printf '%s\n' "$stage/usr/pkg/bin/pkgconf" > "$work/elf-list"
export REQUIRES_FILE="$work/requires-before.txt"
: > "$REQUIRES_FILE"
awk -f "$root/upstream/pkgsrc/mk/check/check-shlibs-elf.awk" < "$work/elf-list" > "$work/elf-before-errors.txt"
[ ! -s "$REQUIRES_FILE" ]
export REQUIRES_FILE="$work/requires-after.txt"
awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" < "$work/elf-list" > "$work/elf-after-errors.txt"
[ ! -s "$work/elf-after-errors.txt" ]
grep -Fxq /usr/lib/libc.so.12 "$REQUIRES_FILE"
grep -Fxq /usr/pkg/lib/libpkgconf.so.8 "$REQUIRES_FILE"
mkdir "$work/empty-sysroot"
CROSS_DESTDIR="$work/empty-sysroot" awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" \
    < "$work/elf-list" > "$work/elf-missing-errors.txt"
grep -q 'missing library: libc.so.12' "$work/elf-missing-errors.txt"
echo 'PASS: target ELF requirements are emitted; a missing target libc is reported'

printf '%s\n' "$stage/usr/pkg/bin/pkgconf" | READELF="$work/no-readelf" \
    awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-missing-tool.txt"
grep -q 'readelf failed' "$work/elf-missing-tool.txt"
awk_path=$(command -v awk)
printf '%s\n' "$stage/usr/pkg/bin/pkgconf" | PATH="$work/no-tools" \
    "$awk_path" -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-missing-od.txt"
grep -q 'cannot read ELF header' "$work/elf-missing-od.txt"
: > "$work/empty-file"
printf '%s\n' "$work/empty-file" | awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-empty.txt"
[ ! -s "$work/elf-empty.txt" ]
mkdir -p "$work/aliases/usr/pkg/bin" "$work/aliases/usr/pkg/lib/private"
cp "$stage/usr/pkg/bin/pkgconf" "$work/aliases/usr/pkg/lib/private/tool"
cp "$stage"/usr/pkg/lib/libpkgconf.so* "$work/aliases/usr/pkg/lib/"
ln -s ../lib/private/tool "$work/aliases/usr/pkg/bin/relative"
ln -s /usr/pkg/lib/private/tool "$work/aliases/usr/pkg/bin/absolute"
ln -s /usr/pkg/lib/private "$work/aliases/usr/pkg/indirect"
ln -s ../indirect/tool "$work/aliases/usr/pkg/bin/directory"
for alias in relative absolute directory; do
    printf '%s\n' "$work/aliases/usr/pkg/bin/$alias" | DESTDIR="$work/aliases" \
        REQUIRES_FILE="$work/requires-$alias" awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-$alias.txt"
    [ ! -s "$work/elf-$alias.txt" ]
    grep -Fxq /usr/lib/libc.so.12 "$work/requires-$alias"
done
ln -s loop "$work/aliases/usr/pkg/bin/loop"
printf '%s\n' "$work/aliases/usr/pkg/bin/loop" | DESTDIR="$work/aliases" \
    awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-loop.txt"
grep -q 'cannot resolve target path' "$work/elf-loop.txt"
printf '\177ELFbad' > "$work/broken-elf"
printf '%s\n' "$work/broken-elf" | awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-malformed.txt"
grep -q 'readelf failed' "$work/elf-malformed.txt"
printf '#!/bin/sh\nexit 0\n' > "$work/script"
printf '%s\n' "$work/script" | READELF="$work/no-readelf" \
    awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-script.txt"
[ ! -s "$work/elf-script.txt" ]
printf '%s\n' "$work/absent" | awk -f "$pkgsrc/mk/check/check-shlibs-elf.awk" > "$work/elf-absent.txt"
grep -q 'cannot read ELF header' "$work/elf-absent.txt"
echo 'PASS: ELF metadata rejects missing tools/files and malformed ELF, and skips scripts'

unset WRKDIR DESTDIR CROSS_DESTDIR READELF PKG_INFO_CMD DEPENDS_FILE REQUIRES_FILE PLATFORM_RPATH PREFIX PACKAGE_PLIST

# Exercise the actual metadata rule; shell-pattern exceptions must stay usable.
for mode in all skip; do
    case "$mode" in all) skip= ;; skip) skip='bin/*' ;; esac
    "$bmake" -C "$pkgsrc/devel/pkgconf" MAKECONF="$makeconf" \
        _BUILD_INFO_FILE="$work/info-$mode" CHECK_SHLIBS_SKIP="$skip" \
        "$work/info-$mode" > "$work/metadata-$mode.log" 2>&1
    cp "$stage/../.elf-requires" "$work/raw-requires-$mode"
done
grep -Fxq /usr/pkg/lib/libpkgconf.so.8 "$work/raw-requires-all"
if grep -Fq /usr/pkg/lib/libpkgconf.so.8 "$work/raw-requires-skip"; then echo "Unexpected matching output" >&2; exit 1; fi
# Package-provided DSOs must remain absent from final REQUIRES.
if grep -Fq 'REQUIRES=/usr/pkg/lib/libpkgconf.so.8' "$work/info-all"; then echo "Unexpected matching output" >&2; exit 1; fi
grep -Fxq 'REQUIRES=/usr/lib/libc.so.12' "$work/info-skip"
echo 'PASS: package metadata honors CHECK_SHLIBS_SKIP without suppressing other dependencies'
