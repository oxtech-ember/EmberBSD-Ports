#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual cross recipe and compiled test payload.
set -eu
[ "$#" = 3 ] || { echo 'Usage: lld-cross-inputs.sh PKGSRC MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
: "${BMAKE:?Set the build-host bmake}"
: "${READELF:?Set the target readelf}"
mkdir "$work"
query() { "$BMAKE" -C "$pkgsrc/devel/lld" MAKECONF="$makeconf" "$@"; }
query -V '${PKG_FAIL_REASON}' > "$work/valid.log"
[ ! -s "$work/valid.log" ] || [ -z "$(cat "$work/valid.log")" ]
for variable in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_CROSS_LLVM_CONFIG EMBERBSD_LLVM_NATIVE_TOOLS; do
    query "$variable=/nonexistent-ember-tool" -V '${PKG_FAIL_REASON}' > "$work/$variable-missing.log"
    grep -q 'must select the matching build-host tool' "$work/$variable-missing.log"
done
query -V '${CMAKE_CONFIGURE_ARGS}' > "$work/options.log"
grep -q -- '-DLLVM_BUILD_TESTS=ON' "$work/options.log"
grep -q -- '-DLLVM_INCLUDE_TESTS=ON' "$work/options.log"
grep -q -- '-DLLVM_INSTALL_TOOLCHAIN_ONLY=OFF' "$work/options.log"
query -V '${EXTRACT_ELEMENTS}' > "$work/extract.log"
grep -q 'libunwind/include' "$work/extract.log"
wrksrc=$(query -V '${WRKSRC}')
wrkdir=$(query -V '${WRKDIR}')
sysroot=$(query -V '${CROSS_DESTDIR}')
real_sysroot=$(CDPATH= cd -- "$sysroot" && pwd -P)
grep -Fq "transform=I:$real_sysroot/usr/pkg:$wrkdir/.buildlink" "$wrkdir/.cwrapper/config/c++"
for test in AsLibAll/LLDAsLibAllTests AsLibELF/LLDAsLibELFTests; do
    name=${test##*/}
    "$READELF" -h -d "$wrksrc/cmake-pkgsrc-build/unittests/$test" > "$work/$name.elf"
    grep -q 'AArch64' "$work/$name.elf"
    grep -q 'NEEDED.*libLLVM.so.23.1' "$work/$name.elf"
    ! grep -E '(RPATH|RUNPATH).*(Volumes|private/tmp|Users)' "$work/$name.elf"
done
for library in COFF Common ELF MachO MinGW Wasm; do
    test -s "$wrkdir/.destdir/usr/pkg/lib/liblld$library.a"
done
echo 'PASS: actual LLD cross inputs, missing tools rejected, complete format libraries and both upstream AArch64 test executables'
