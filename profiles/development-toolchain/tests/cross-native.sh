#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc metadata of the GCC16 target
# compiler built on another host (build != host == target). No build runs.
set -eu
[ "$#" = 3 ] || { echo 'Usage: cross-native.sh PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set the native bmake executable}"
prepared=$(CDPATH= cd -- "$1" && pwd)
conf=$2
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
query() {
    "$BMAKE" -C "$prepared/lang/gcc16" "MAKECONF=$conf" "$@"
}
query -V 'name=${PKGNAME}' -V 'platform=${MACHINE_GNU_PLATFORM}' \
    -V 'tools=${TOOLDIR}' -V 'sysroot=${CROSS_DESTDIR}' -V 'fail=${PKG_FAIL_REASON}' \
    -V 'deps=${DEPENDS}' > "$work/cross.txt"
value() { sed -n "s/^$1=//p" "$work/cross.txt"; }
[ "$(value name)" = gcc16-16.2.0nb5 ]
platform=$(value platform) tools=$(value tools) sysroot=$(value sysroot)
case "$platform" in aarch64--netbsd|x86_64--netbsd) ;; *) exit 1 ;; esac
[ -z "$(value fail)" ] || { value fail >&2; exit 1; }
value deps | tr ' ' '\n' | grep -qx 'binutils>=2.47:../../devel/binutils'
query -V '${CONFIGURE_ARGS}' -V '${CONFIGURE_ARGS.NetBSD}' | tr ' ' '\n' > "$work/args.txt"
query -V '${CONFIGURE_ENV}' | tr ' ' '\n' > "$work/env.txt"
grep -qx -- "--target=$platform" "$work/args.txt"
grep -qx -- "--host=$platform" "$work/args.txt"
grep -qx -- "--with-build-sysroot=$sysroot" "$work/args.txt"
# The installed driver must not name a build-host or base assembler/linker.
if grep -E -- '^--with-(as|ld)=' "$work/args.txt"; then exit 1; fi
grep -qx -- '--with-gnu-as' "$work/args.txt"
for tool in AR AS LD NM OBJCOPY OBJDUMP RANLIB READELF STRIP; do
    lower=$(printf '%s' "$tool" | tr 'A-Z' 'a-z')
    grep -qx "${tool}_FOR_TARGET=$tools/bin/$platform-$lower" "$work/env.txt"
done
# Target libraries get the in-tree driver defaults. libstdc++ probes must not
# read the installed C++ headers.
for compiler in CC CXX; do
    [ "$(query -V "\${CONFIGURE_ENV:M${compiler}_FOR_TARGET=*}")" = \
        "$(query -V "${compiler}_FOR_TARGET=\${_GCC16_${compiler}_FOR_TARGET:Q}")" ]
done
cc=$(query -V '${_GCC16_CC_FOR_TARGET}') cxx=$(query -V '${_GCC16_CXX_FOR_TARGET}')
case "$cc" in "$tools/bin/$platform-gcc "*) ;; *) exit 1 ;; esac
case "$cxx" in "$tools/bin/$platform-g++ -nostdinc++ "*) ;; *) exit 1 ;; esac
if [ "$platform" = x86_64--netbsd ]; then
    for flag in -march=nocona -mtune=nocona -mfpmath=sse; do
        case " $cc " in *" $flag "*) ;; *) exit 1 ;; esac
    done
fi
for flag in CFLAGS CXXFLAGS; do grep -qx "${flag}_FOR_TARGET=-O2" "$work/env.txt"; done
# The installed fixincl and mkheaders use target tools.
query -V '${MAKE_ENV:Mac_cv_path_SED=*:[-1]}' | grep -qx 'ac_cv_path_SED=/usr/bin/sed'
for flag in CPPFLAGS LDFLAGS; do grep -qx "${flag}_FOR_BUILD=" "$work/env.txt"; done
for flag in CFLAGS CXXFLAGS; do grep -qx "${flag}_FOR_BUILD=-O2" "$work/env.txt"; done
native_ar=$(query -V '${NATIVE_AR}')
case "$native_ar" in /*) grep -qx "AR_FOR_BUILD=$native_ar" "$work/env.txt" ;; *) exit 1 ;; esac
query NATIVE_AR= -V '${PKG_FAIL_REASON}' | grep -q 'Set NATIVE_AR and NATIVE_RANLIB'
# The driver finds the Binutils dependency in its private program directory.
query -V '${GCC16_BINUTILS_DIR}' | grep -qx "/usr/pkg/$platform/bin"
query -V '${.ALLTARGETS}' | tr ' ' '\n' | grep -qx gcc16-cross-target-paths
# Native builds keep the upstream configuration.
query USE_CROSS_COMPILE=no -V '${CONFIGURE_ARGS}' -V '${DEPENDS}' > "$work/native.txt"
if grep -E -- '--target=|--with-build-sysroot=|binutils>=2.47' "$work/native.txt"; then exit 1; fi
echo 'PASS: cross target compiler metadata selects cross probes, target tools and Binutils 2.47; native metadata unchanged'
