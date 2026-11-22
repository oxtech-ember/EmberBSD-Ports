#!/bin/bash
# Copyright (c) 2026 EmberBSD contributors.
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
set -euo pipefail
work=$1
seed=$2
src=$work/export/pkgsrc
prefix=$work/prefix
mkdir -p "$work/logs"
test "$(uname -sm)" = 'Linux x86_64'
for tool in clang clang++ llvm-readelf llvm-ar llvm-ranlib llvm-nm llvm-strip ld.lld; do
    test -x "$seed/bin/$tool"
done
export CC="$seed/bin/clang" CXX="$seed/bin/clang++" CPP="$seed/bin/clang -E" CLANGBASE="$seed"
printf 'TOOLS_PATH.readelf=%s/bin/llvm-readelf\n' "$seed" >"$work/bootstrap.mk"
cat >"$work/seed.mk" <<MAKE
.if defined(BSD_PKG_MK)
.include "$src/EMBERBSD-DEFAULTS-MK.CONF"
WRKOBJDIR=$work/obj
DISTDIR=$work/distfiles
PACKAGES=$work/packages
MAKE_JOBS=$(nproc)
PKGSRC_COMPILER=clang
CLANGBASE=$seed
CC=$seed/bin/clang
CXX=$seed/bin/clang++
CPP=$seed/bin/clang -E
PKG_OPTIONS.libfetch+=openssl
TOOLS_PATH.readelf=$seed/bin/llvm-readelf
TOOLS_PLATFORM.readelf=$seed/bin/llvm-readelf
.endif
MAKE
for pair in 'ar llvm-ar' 'ranlib llvm-ranlib' 'nm llvm-nm' 'strip llvm-strip' 'ld ld.lld' 'as as'; do
    read -r name tool <<<"$pair"
    provider="$seed/bin/$tool"
    if [[ $name = as ]]; then provider=/usr/bin/as; fi
    printf 'PKG_%s=%s\n%s=%s\nTOOLS_PLATFORM.%s=%s\n' "${name^^}" "$provider" "${name^^}" "$provider" "$name" "$provider" >>"$work/seed.mk"
done
"$src/bootstrap/bootstrap" --unprivileged --compiler clang --prefix "$prefix" \
    --workdir "$work/bootstrap" --pkgdbdir "$prefix/pkgdb" \
    --bootstrap-mk-fragment "$work/bootstrap.mk" --mk-fragment "$work/seed.mk" \
    >"$work/logs/bootstrap.log" 2>&1 || { tail -100 "$work/logs/bootstrap.log"; exit 1; }
export PATH="$prefix/bin:$prefix/sbin:$PATH"
build() {
    local recipe=$1
    shift
    local log="$work/logs/${recipe##*/}.log"
    "$prefix/bin/bmake" -C "$src/$recipe" "$@" >"$log" 2>&1 || { tail -100 "$log"; return 1; }
}
build shells/mksh package-install
printf 'SH=%s/bin/mksh\nCONFIG_SHELL=%s/bin/mksh\nTOOLS_PLATFORM.sh=%s/bin/mksh\n' "$prefix" "$prefix" "$prefix" >>"$prefix/etc/mk.conf"
printf 'EMBERBSD_NATIVE_BOOTSTRAP=yes\n' >>"$prefix/etc/mk.conf"
build devel/cmake package-install
