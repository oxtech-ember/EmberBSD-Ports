#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The installed zlib 1.3.2 header must
# compile with -Werror=undef and keep its HAVE_* selection semantics.
set -eu
[ "$#" = 2 ] || { echo 'Usage: zlib-wundef.sh DISTFILES NEW_WORK' >&2; exit 2; }
: "${CC:?Set a host C compiler}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
distfiles=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir "$work/src"
tar -xJf "$distfiles/zlib-1.3.2.tar.xz" -C "$work/src" --strip-components=1 \
    zlib-1.3.2/zconf.h zlib-1.3.2/zlib.h
cat > "$work/t.c" <<'EOT'
#include "zlib.h"
#if defined(EXPECT_UNISTD) != defined(Z_HAVE_UNISTD_H)
#error Z_HAVE_UNISTD_H selection changed
#endif
#if defined(EXPECT_STDARG) != defined(Z_HAVE_STDARG_H)
#error Z_HAVE_STDARG_H selection changed
#endif
int main(void) { return 0; }
EOT
check() { "$CC" -Wundef -Werror -fsyntax-only -I"$work/src" "$@" "$work/t.c"; }
# The unchanged upstream header shows the defect.
if check 2>/dev/null; then echo 'Unpatched zconf.h unexpectedly passed -Werror=undef' >&2; exit 1; fi
patch -f -N -F 0 -s -d "$work/src" < "$root/profiles/common-build-tools/recipes/devel/zlib/patches/patch-zconf.h"
check
check -DHAVE_UNISTD_H=0 -DHAVE_STDARG_H=0
check -DHAVE_UNISTD_H=1 -DEXPECT_UNISTD -DHAVE_STDARG_H=1 -DEXPECT_STDARG
check -DHAVE_UNISTD_H -DEXPECT_UNISTD
if patch -f -N -F 0 -s -d "$work/src" < "$root/profiles/common-build-tools/recipes/devel/zlib/patches/patch-zconf.h" > /dev/null 2>&1; then exit 1; fi
echo 'PASS: zlib 1.3.2 header compiles with -Werror=undef; undefined and zero HAVE_* stay unset, nonzero values select Z_HAVE_*'
