#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted staged GCC16 runtime bootstrap.
set -eu
usage() {
    echo 'Usage: build.sh [--check] [--resume] --target amd64|aarch64 EXPORTED_PKGSRC GCC_ARCHIVE KERNEL_PREFIX SYSROOT HOST_MATH_PREFIX WORK' >&2
    exit 2
}
fail() { echo "$*" >&2; exit 2; }
check=no
resume=no
while :; do
    case ${1:-} in
        --check) check=yes; shift;;
        --resume) resume=yes; shift;;
        *) break;;
    esac
done
[ "$#" -ge 2 ] && [ "$1" = --target ] || usage
target=$2
shift 2
case "$target" in
    amd64) triplet=x86_64--netbsd; machine='Advanced Micro Devices X86-64'; arch=__x86_64__;
        target_flags='-O2 -march=nocona -mtune=nocona -mfpmath=sse';;
    aarch64) triplet=aarch64--netbsd; machine=AArch64; arch=__aarch64__;
        target_flags=-O2;;
    *) fail "Unsupported target: $target";;
esac
[ "$#" -eq 6 ] || usage
pkgsrc=$1 archive=$2 kernel=$3 sysroot=$4 math=$5 work=$6
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
profile=$(CDPATH= cd -- "$here/.." && pwd -P)
recipe=$pkgsrc/lang/gcc16
for path in "$@"; do
    case "$path" in /*) ;; *) fail 'Absolute paths required.';; esac
    case "$path" in *[!A-Za-z0-9_./-]*) fail 'Use paths without whitespace or shell metacharacters.';; esac
done
if [ "$resume" = no ]; then
    [ ! -e "$work" ] && [ ! -L "$work" ] || fail 'NEW_WORK already exists.'
else
    [ -d "$work" ] && [ ! -L "$work" ] || fail 'Resume requires an existing work directory.'
    work=$(CDPATH= cd -- "$work" && pwd -P)
fi
sysroot=$(CDPATH= cd -- "$sysroot" && pwd -P) || fail 'Missing target sysroot.'
jobs=${CROSS_JOBS-4}
case "$jobs" in ''|*[!0-9]*|0) fail 'CROSS_JOBS must be positive.';; esac
origin=${EMBERBSD_SYSROOT_SOURCE:-}
case "$origin" in ''|*[!0-9a-f]*) fail 'Set EMBERBSD_SYSROOT_SOURCE to the verified full EmberBSD source commit.';; esac
[ "${#origin}" -eq 40 ] || fail 'Use a full EmberBSD source commit.'
provenance=${EMBERBSD_SYSROOT_PROVENANCE:-}
if [ -n "$provenance" ]; then
    case "$provenance" in /*) ;; *) fail 'Use an absolute seed provenance path.';; esac
    [ -f "$provenance" ] || fail 'Missing seed provenance file.'
fi
cc=$kernel/bin/$triplet-gcc
cxx=$kernel/bin/$triplet-g++
readelf=$kernel/bin/$triplet-readelf
for tool in gcc g++ ar as ld nm objcopy objdump ranlib readelf strip; do
    [ -x "$kernel/bin/$triplet-$tool" ] || fail "Missing host cross tool: $tool"
done
for compiler in "$cc" "$cxx"; do
    [ "$("$compiler" -dumpmachine)" = "$triplet" ] || fail 'Compiler target mismatch.'
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || fail 'GCC 16.2.0 is required.'
done
macros=$(printf '\n' | "$cc" -dM -E -x c -)
for definition in '#define __GNUC__ 16' '#define __NetBSD__ 1' '#define __SIZEOF_POINTER__ 8' "#define $arch 1"; do
    printf '%s\n' "$macros" | grep -qx "$definition" || fail 'Compiler target ABI mismatch.'
done
for header in stddef.h stdio.h pthread.h math.h; do
    [ -f "$sysroot/usr/include/$header" ] || fail "Missing target header: $header"
done
check_elf() {
    object=$1
    [ -f "$object" ] || fail "Missing target ELF: $object"
    # Reject host-resolved absolute links and links outside the supplied tree.
    resolved=$(realpath "$object") || fail 'Cannot resolve target ELF.'
    case "$resolved" in "$2"/*) ;; *) fail 'A target ELF symlink escapes its tree.';; esac
    elf_header=$("$readelf" -h "$object") || fail 'Cannot inspect target ELF.'
    printf '%s\n' "$elf_header" | grep -Eq 'Class:[[:space:]]+ELF64' || fail 'Target ELF must be 64-bit.'
    actual_machine=$(printf '%s\n' "$elf_header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')
    [ "$actual_machine" = "$machine" ] || fail 'Target ELF architecture mismatch.'
}
for name in libc.so.12 libpthread.so.1 libm.so.0 crt0.o; do
    check_elf "$sysroot/usr/lib/$name" "$sysroot"
done
for item in gmp:__GNU_MP_VERSION:6:__GNU_MP_VERSION_MINOR:3:__GNU_MP_VERSION_PATCHLEVEL:0 \
    mpfr:MPFR_VERSION_MAJOR:4:MPFR_VERSION_MINOR:2:MPFR_VERSION_PATCHLEVEL:2 \
    mpc:MPC_VERSION_MAJOR:1:MPC_VERSION_MINOR:4:MPC_VERSION_PATCHLEVEL:1; do
    library=${item%%:*}; rest=${item#*:}
    [ -f "$math/lib/lib$library.a" ] || fail "Missing host static library: $library"
    while [ -n "$rest" ]; do
        macro=${rest%%:*}; rest=${rest#*:}; value=${rest%%:*}
        if [ "$rest" = "$value" ]; then rest=; else rest=${rest#*:}; fi
        actual=$(awk -v macro="$macro" '$1 == "#define" && $2 == macro {print $3}' "$math/include/$library.h")
        [ "$actual" = "$value" ] || fail "Host $library version mismatch."
    done
done
. "$here/audit-source.sh"
kernel_receipt=$kernel/../inputs.txt
[ -f "$kernel_receipt" ] && grep -qx 'mode=kernel' "$kernel_receipt" || fail 'Missing audited kernel compiler inputs.txt receipt.'
for input_hash in "$expected" "$(shasum -a 256 "$recipe/distinfo" | awk '{print $1}')"; do
    grep -Eq "^$input_hash[[:space:]]" "$kernel_receipt" || fail 'Kernel compiler source or patch receipt does not match.'
done
make=${GNU_MAKE:-}
if [ -z "$make" ]; then make=$(command -v gmake || command -v make) || fail 'GNU make is required.'; fi
case "$make" in /*) ;; *) fail 'GNU_MAKE must be an absolute executable path.';; esac
[ -x "$make" ] && "$make" --version | grep -q '^GNU Make ' || fail 'GNU make is required.'
. "$here/target-tools.sh"
. "$here/resume-state.sh"
[ "$resume" = no ] || check_resume
printf 'target=%s\ntriplet=%s\nabi=libstdc++.so.7\ntarget_flags=%s\n' "$target" "$triplet" "$target_flags"
printf 'seed_source=%s\nruntime_prefix=/usr/pkg/gcc16\nstage=%s/stage\n' "$origin" "$work"
printf 'ar_for_target=%s\nnm_for_target=%s\n' "$AR_FOR_TARGET" "$NM_FOR_TARGET"
[ "$check" = no ] || exit 0

if [ "$resume" = no ]; then
mkdir "$work"
work=$(CDPATH= cd -- "$work" && pwd -P)
mkdir "$work/build" "$work/stage"
{
    uname -srm
    printf 'scope=runtime-only-bootstrap\ntarget=%s\ntriplet=%s\nseed_source=%s\n' "$target" "$triplet" "$origin"
    printf 'kernel=%s\nsysroot=%s\nmath=%s\njobs=%s\n' "$kernel" "$sysroot" "$math" "$jobs"
    printf 'host_cc=%s\nhost_cxx=%s\nhost_cflags=%s\nhost_cxxflags=%s\n' \
        "${HOST_CC:-cc}" "${HOST_CXX:-c++}" "${HOST_CFLAGS:--O2}" "${HOST_CXXFLAGS:--O2}"
    "$cc" --version
    "$cxx" --version
    "$make" --version
    shasum -a 256 "$archive" "$recipe/distinfo" "$recipe/Makefile" "$recipe/Makefile.common" "$kernel_receipt" \
        "$cc" "$cxx" "$readelf" "$math/lib/libgmp.a" "$math/lib/libmpfr.a" "$math/lib/libmpc.a"
    for name in $patches; do shasum -a 256 "$recipe/patches/$name"; done
    for name in stddef.h stdio.h pthread.h math.h; do shasum -a 256 "$sysroot/usr/include/$name"; done
    for name in libc.so.12 libpthread.so.1 libm.so.0 crt0.o; do shasum -a 256 "$sysroot/usr/lib/$name"; done
    [ -z "$provenance" ] || shasum -a 256 "$provenance"
} > "$work/inputs.txt"
# Verify the host GMP contract used by the existing compiler workflow.
${HOST_CC:-cc} ${HOST_CFLAGS:--O2} -I"$math/include" "$profile/cross/tests/host-gmp.c" \
    "$math/lib/libgmp.a" -o "$work/host-gmp"
"$work/host-gmp" > "$work/host-gmp.log"
"$work/host-gmp" timer >> "$work/host-gmp.log"
sh "$here/prepare-source.sh" "$pkgsrc" "$archive" "$work/src" > "$work/patch.log" 2>&1
else
    backup_resume
fi
# Pin the helper revision and all target tools, including when an older
# receipt predates explicit binutils selection. Keep the original receipt.
{
    printf 'target_binutils=audited-kernel-prefix\n'
    for bootstrap_tool in ar as ld nm objcopy objdump ranlib readelf strip; do
        shasum -a 256 "$kernel/bin/$triplet-$bootstrap_tool"
        "$kernel/bin/$triplet-$bootstrap_tool" --version | sed -n '1p'
    done
    shasum -a 256 "$here/build.sh" "$here/target-tools.sh" "$here/resume-state.sh" \
        "$here/audit-source.sh" "$here/prepare-source.sh" "$make" \
        "$work/src/configure" "$work/src/gcc/configure" "$work/src/libstdc++-v3/configure"
} >> "$work/inputs.txt"
cd "$work/build"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH CONFIG_SITE
set -- --target="$triplet" --prefix=/usr/pkg/gcc16 --libdir=/usr/pkg/gcc16/lib \
    --with-local-prefix=/usr/pkg/gcc16 --with-gxx-include-dir=/usr/pkg/gcc16/include/c++ \
    --with-sysroot="$sysroot" --with-native-system-header-dir=/usr/include \
    --with-gmp="$math" --with-mpfr="$math" --with-mpc="$math" \
    --with-gnu-as --with-gnu-ld --with-as="$kernel/bin/$triplet-as" --with-ld="$kernel/bin/$triplet-ld" \
    --enable-languages=c,c++ --disable-bootstrap --disable-multilib \
    --enable-shared --enable-threads=posix --enable-long-long --disable-libssp \
    --disable-libstdcxx-pch --without-zstd --without-isl --disable-nls
if [ "$target" = amd64 ]; then
    set -- "$@" --with-arch=nocona --with-tune=nocona --with-fpmath=sse
fi
# Preserve the NetBSD recipe's supported API cache choices.
export ac_cv_func_clock_gettime=yes ac_cv_func_gethostbyname_r=no
export ac_cv_func_freelocale=no ac_cv_func_newlocale=no ac_cv_func_uselocale=no
export CFLAGS_FOR_TARGET="$target_flags" CXXFLAGS_FOR_TARGET="$target_flags"
export LDFLAGS_FOR_TARGET='-Wl,-rpath,/usr/pkg/gcc16/lib'
CC=${HOST_CC:-cc} CXX=${HOST_CXX:-c++} CFLAGS=${HOST_CFLAGS:--O2} CXXFLAGS=${HOST_CXXFLAGS:--O2} \
    "$work/src/configure" "$@" > "$work/configure.log" 2>&1
# The kernel-only compiler has single-thread gthr headers. Rebuild host
# frontends with POSIX threads; install only target libraries below.
"$make" -j"$jobs" all-gcc > "$work/frontends.log" 2>&1
"$work/build/gcc/xgcc" -v 2> "$work/frontend-version.txt"
grep -qx 'Thread model: posix' "$work/frontend-version.txt" || fail 'Runtime compiler does not select POSIX threads.'
"$make" -j"$jobs" all-target-libgcc all-target-libstdc++-v3 > "$work/runtime-build.log" 2>&1
"$make" "DESTDIR=$work/stage" install-target-libgcc install-target-libstdc++-v3 > "$work/runtime-install.log" 2>&1
runtime=$work/stage/usr/pkg/gcc16
for crt in crtbegin.o crtbeginS.o crtend.o crtendS.o; do
    check_elf "$runtime/lib/gcc/$triplet/16.2.0/$crt" "$work/stage"
done
for library in libgcc_s.so.1 libstdc++.so.7; do
    check_elf "$runtime/lib/$library" "$work/stage"
    "$readelf" -d "$runtime/lib/$library" > "$work/$library.dynamic"
    grep -F "[$library]" "$work/$library.dynamic" | grep -q SONAME || fail 'Runtime SONAME mismatch.'
    for host_path in "$work" "$sysroot" "$kernel" "$math"; do
        if grep -F "$host_path" "$work/$library.dynamic" >/dev/null; then
            fail 'Build-host path leaked into runtime dynamic tags.'
        fi
    done
done
[ -f "$runtime/include/c++/vector" ] && [ -f "$runtime/include/c++/$triplet/bits/c++config.h" ] || fail 'Missing installed C++ headers.'
cd "$work/stage"
find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort > "$work/stage.sha256"
find . -type l -exec sh -c 'for path do printf "%s\t%s\n" "$path" "$(readlink "$path")"; done' sh {} + | LC_ALL=C sort > "$work/stage.symlinks"
printf 'runtime-only-bootstrap\n' > "$work/build-success"
printf 'Staged target runtime: %s\n' "$runtime"
echo 'This is not a complete gcc16 package or runtime acceptance.'
