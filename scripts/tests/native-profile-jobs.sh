#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Read the real profiles and pkgsrc build flags without building packages.
# Usage: native-profile-jobs.sh BMAKE PREPARED_PKGSRC
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/native-profile-jobs.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp "$root/profiles/common-graphics/mk.conf" "$work/graphics.mk"
cp "$root/profiles/common-media/mk.conf" "$work/media.mk"
cp "$root/pkgsrc/plasma-toolkit.mk.conf" "$work/plasma.mk"
touch "$work/EMBERBSD-COMMON-TOOLS-MK.CONF" \
    "$work/EMBERBSD-COMMON-GRAPHICS-SOURCES" \
    "$work/EMBERBSD-COMMON-MEDIA-SOURCES"
cat > "$work/case.mk" <<'MAKE'
BSD_PKG_MK= yes
PKGPATH= devel/ember-jobs-fixture
OPSYS= NetBSD
OS_VERSION= 11.0
MACHINE_ARCH= aarch64
PREFIX= /usr/pkg
LOCALBASE= /usr/pkg
EMBERBSD_COMMON_TOOLS= yes
USE_BUILTIN.MesaLib= no
USE_BUILTIN.libdrm= no
USE_BUILTIN.glu= no
.include "${MAKECONF}"
_COOKIE.build= ${.CURDIR}/unused-build-cookie
_CLEANING= no
BUILD_DIRS= .
WRKSRC= /unused
.include "${BUILD_MK}"
MAKE
for config in default budget; do
    if [ "$config" = budget ]; then
        printf 'MAKE_JOBS= 4\n' > "$work/$config.conf"
    else
        : > "$work/$config.conf"
    fi
    cat >> "$work/$config.conf" <<'MAKE'
.if ${PROFILE} == "graphics" || ${PROFILE} == "chain"
.include "${.PARSEDIR}/graphics.mk"
.endif
.if ${PROFILE} == "plasma"
EMBERBSD_COMMON_GRAPHICS= yes
EMBERBSD_COMMON_MEDIA= yes
.endif
.if ${PROFILE} == "chain"
.include "${.PARSEDIR}/media.mk"
.endif
.if ${PROFILE} == "plasma" || ${PROFILE} == "chain"
.include "${.PARSEDIR}/plasma.mk"
.endif
MAKE
done
failures=0
check() {
    label=$1 expected=$2 config=$3
    shift 3
    actual=$("$bmake" -r -f "$work/case.mk" MAKECONF="$work/$config.conf" \
        BUILD_MK="$tree/mk/build/build.mk" "$@" \
        -V '${MAKE_JOBS:Uunset}|${_MAKE_JOBS:U}|${_MAKE_JOBS_N}|${PKG_FAIL_REASON:U}')
    if [ "$actual" != "$expected" ]; then
        echo "FAIL: $label: expected $expected; got $actual" >&2
        failures=$((failures + 1))
    fi
}
for profile in graphics plasma; do
    check "$profile native default" '1|-j1|1|' default PROFILE="$profile"
    check "$profile earlier MAKECONF budget" '4|-j4|4|' budget PROFILE="$profile"
done
check 'profile chain default' '1|-j1|1|' default PROFILE=chain
check 'profile chain command-line override' '6|-j6|6|' budget PROFILE=chain MAKE_JOBS=6
check 'unsafe recipe stays serial' '4||1|' budget PROFILE=chain MAKE_JOBS_SAFE=no
check 'cross target budget' '4|-j4|4|' budget PROFILE=chain USE_CROSS_COMPILE=yes \
    EMBERBSD_COMMON_GRAPHICS_CROSS=yes EMBERBSD_CROSS_COMPILER_FAMILY=clang \
    PKGSRC_COMPILER=clang CLANGBASE=/tools EMBERBSD_CROSS_TOOLS=/tools TOOLDIR=/tools \
    EMBERBSD_CROSS_SYSROOT=/sysroot CROSS_DESTDIR=/sysroot \
    EMBERBSD_CROSS_HOST_PREFIX=/host CROSS_LOCALBASE=/usr/pkg \
    CROSS_MACHINE_ARCH=aarch64 CROSS_OPSYS=NetBSD
check 'cross native tools budget' '4|-j4|4|' budget PROFILE=chain \
    EMBERBSD_COMMON_GRAPHICS_CROSS=yes USE_CROSS_COMPILE=no
check 'cross native tools keep their own default' 'unset||1|' default PROFILE=chain \
    EMBERBSD_COMMON_GRAPHICS_CROSS=yes USE_CROSS_COMPILE=no
[ "$failures" -eq 0 ] || exit 1
echo 'PASS: native profile defaults, caller budgets, recipe safety and cross/native-tool exceptions'
