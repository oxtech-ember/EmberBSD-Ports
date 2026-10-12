#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, actual exported shared-version selection regression.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
make=${BMAKE:-bmake}
command -v "$make" >/dev/null 2>&1 || { echo 'SKIP: BSD make unavailable; native selection parsing required'; exit 0; }
# Only platform preferences are substituted. The selection and version block
# are the actual exported file, not a rewritten predicate.
sed 's@\.include "../../mk/bsd.prefs.mk"@.include "prefs.mk"@' \
    "$tree/lang/llvm/version.mk" > "$work/version.mk"
printf 'OPSYS= NetBSD\nOS_VERSION= 11.99\n' > "$work/prefs.mk"
cat > "$work/Makefile" <<'MAKE'
.include "version.mk"
all:
	@if test -n '${PKG_FAIL_REASON:U}'; then \
	    printf '%s\n' '${PKG_FAIL_REASON:U}'; exit 1; fi
	@test '${LLVM_VERSION}' = 23.1.3
	@test '${DISTNAME}' = llvm-project-23.1.3.src
MAKE
for path in lang/llvm lang/clang devel/lld devel/py-llvm-lit; do
    (cd "$work" && "$make" PKGPATH="$path")
    echo "PASS: selected $path"
done
for path in devel/lldb devel/polly lang/clang-tools-extra lang/compiler-rt \
    lang/flang lang/libclc lang/libcxx lang/libcxxabi lang/libunwind lang/mlir \
    lang/wasi-compiler-rt lang/wasi-libcxx parallel/openmp; do
    if (cd "$work" && "$make" PKGPATH="$path") > "$work/${path##*/}.log" 2>&1; then
        echo "FAIL: unprepared family accepted: $path" >&2; exit 1
    fi
    grep -q 'is not prepared in the common profile' "$work/${path##*/}.log"
    echo "PASS: rejected $path"
done
