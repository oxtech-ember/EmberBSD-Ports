#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run actual CPython configure with cross GCC16.
set -eu
[ "$#" = 6 ] || { echo "Usage: $0 BASELINE_SOURCE PATCHED_SOURCE CROSS_PREFIX SYSROOT HOST_PYTHON NEW_WORK" >&2; exit 2; }
baseline=$1 patched=$2 prefix=$3 sysroot=$4 python=$5 work=$6
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./+-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Output already exists.' >&2; exit 2; }
[ "$("$prefix/bin/x86_64--netbsd-gcc" -dumpmachine)" = x86_64--netbsd ]
[ "$("$prefix/bin/x86_64--netbsd-gcc" -dumpfullversion)" = 16.2.0 ]
[ "$("$python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" = 3.15 ]
[ -f "$sysroot/usr/include/stddef.h" ]
[ -f "$sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/crtbegin.o" ]
mkdir "$work"
build=$(sh "$patched/config.guess")
export CC="$prefix/bin/x86_64--netbsd-gcc --sysroot=$sysroot -B$sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/"
export CXX="$prefix/bin/x86_64--netbsd-g++ --sysroot=$sysroot -B$sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/"
export CFLAGS='-O2 -std=gnu17'
export CPPFLAGS="-I$sysroot/usr/include -I$sysroot/usr/pkg/include"
export LDFLAGS="-L$sysroot/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -L$sysroot/usr/lib -L$sysroot/usr/pkg/lib"
export LIBS=-lcrypt
export CONFIG_SITE=/dev/null
export PKG_CONFIG=${PKG_CONFIG:-pkg-config}
export PKG_CONFIG_SYSROOT_DIR="$sysroot"
export PKG_CONFIG_LIBDIR="$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig"
export LC_ALL=C
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH
configure()
{
    source=$1 output=$2 host=${3:-x86_64--netbsd}
    mkdir "$output"
    # These cross answers already belong to the normal Python315 recipe.
    # Add no cache answers to bypass a new unsupported configure probe.
    (cd "$output" && "$source/configure" --enable-shared \
        --with-openssl="$sysroot/usr" --with-system-expat --without-ensurepip \
        ac_cv_header_uuid_h=false --with-build-python="$python" \
        MACHDEP=netbsd11 _PYTHON_HOST_PLATFORM=netbsd-x86_64 \
        ac_sys_system=NetBSD ac_cv_buggy_getaddrinfo=false \
        --without-pymalloc --with-readline=readline \
        ac_cv_file__dev_ptmx=yes ac_cv_file__dev_ptc=no \
        --prefix=/usr/pkg --build="$build" --host="$host" \
        --mandir=/usr/pkg/man --enable-option-checking=yes)
}
if configure "$baseline" "$work/baseline" > "$work/baseline.log" 2>&1; then
    echo 'Baseline unexpectedly accepted amd64.' >&2; exit 1
fi
grep -Fq 'cross build not supported for x86_64--netbsd' "$work/baseline.log"
echo 'PASS: actual baseline configure rejects the amd64 cross target'
configure "$patched" "$work/candidate" > "$work/candidate.log" 2>&1 || {
    tail -n 20 "$work/candidate.log" >&2; exit 1;
}
grep -Eq '^MACHDEP=[[:space:]]*netbsd11$' "$work/candidate/Makefile"
grep -Eq '^_PYTHON_HOST_PLATFORM=[[:space:]]*netbsd11-x86_64$' "$work/candidate/Makefile"
grep -Eq '^#define SIZEOF_VOID_P 8$' "$work/candidate/pyconfig.h"
grep -Eq '^#define SIZEOF_LONG 8$' "$work/candidate/pyconfig.h"
echo 'PASS: actual GCC16 configure completes with NetBSD amd64 platform and LP64 ABI'
if configure "$patched" "$work/unsupported" riscv64--netbsd > "$work/unsupported.log" 2>&1; then
    echo 'Unsupported NetBSD architecture unexpectedly accepted.' >&2; exit 1
fi
grep -Fq 'cross build not supported for riscv64--netbsd' "$work/unsupported.log"
echo 'PASS: actual configure retains the unsupported NetBSD architecture barrier'
echo 'PASS: configure only; no target interpreter built, installed or executed'
