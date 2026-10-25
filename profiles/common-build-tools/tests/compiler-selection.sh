#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real pkgsrc compiler/dependency regression.
# Target and installed-package receipts are metadata, not native execution.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
make=${BMAKE:-bmake}
arch=${EMBERBSD_TEST_ARCH:-aarch64}
case "$arch" in aarch64|x86_64) ;; *) echo 'Unsupported test architecture.' >&2; exit 2;; esac
command -v "$make" >/dev/null 2>&1 || { echo 'BSD make is required.' >&2; exit 2; }
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir "$work/sys" "$work/mesa-generators"
# Parsing the actual Iris recipe requires a sealed-generator location. This
# empty receipt only exercises metadata; no generator or build is executed.
: > "$work/mesa-generators/installed.sha256"
cat > "$work/sys/bsd.own.mk" <<'MK'
# Only target MAKECONF inclusion is provided by the host boundary.
.if exists(${MAKECONF})
.include "${MAKECONF}"
.endif
MK
cat > "$work/pkg-info" <<'INFO'
#!/bin/sh
# Only the complete GCC package has an installed target receipt.
case "$*" in
    '-qe gcc16') exit 0 ;;
    '-f gcc16') printf 'File: gcc16/bin/gcc\n'; exit 0 ;;
esac
exit 1
INFO
chmod +x "$work/pkg-info"
# Actual pkgtools matching, with the established narrow host C boundary.
cp "$tree/pkgtools/pkg_install/files/lib/dewey.c" "$work/dewey.c"
cp "$tree/pkgtools/pkg_install/files/lib/dewey.h" "$work/dewey.h"
printf '#include <sys/types.h>\n' > "$work/nbcompat.h"
cat > "$work/defs.h" <<'C'
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <err.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
C
"${CC:-cc}" -DHAVE_CTYPE_H=1 -DHAVE_STDLIB_H=1 -I"$work" \
    "$work/dewey.c" "$root/profiles/common-graphics/tests/pkg-admin-boundary.c" \
    -o "$work/pkg-admin"
printf '.include "%s/EMBERBSD-COMMON-TOOLS-MK.CONF"\n' "$tree" > "$work/tools.conf"
printf '.include "%s/EMBERBSD-DEVELOPMENT-MK.CONF"\n' "$tree" > "$work/bootstrap.conf"
: > "$work/plain.conf"
cp "$work/tools.conf" "$work/graphics.conf"
printf '.include "%s/EMBERBSD-COMMON-GRAPHICS-MK.CONF"\n' "$tree" >> "$work/graphics.conf"
cp "$work/graphics.conf" "$work/media.conf"
printf '.include "%s/EMBERBSD-COMMON-MEDIA-MK.CONF"\n' "$tree" >> "$work/media.conf"
# Propagate the same real-make/target boundary to pkg-build-options recursion.
# The wrapper queries real dependency recipes, never supplies blanket options.
cat > "$work/host-make" <<MAKE
#!/bin/sh
    exec "$make" -r -m "$work/sys" \
        OPSYS=NetBSD OS_VERSION=11.0 OPSYS_VERSION=110000 \
        NATIVE_OPSYS=NetBSD NATIVE_OS_VERSION=11.0 NATIVE_OPSYS_VERSION=110000 \
        LOWER_OPSYS=netbsd MACHINE_ARCH=$arch HOST_MACHINE_ARCH=$arch \
        MACHINE_GNU_ARCH=$arch MACHINE_CPU=$arch OBJECT_FMT=ELF \
        LOCALBASE=/usr/pkg PREFIX=/usr/pkg X11_TYPE=native CC=cc CXX=c++ \
        _GCC_VERSION=12.5.0 PKG_INFO="$work/pkg-info" PKG_ADMIN="$work/pkg-admin" \
        PKG_BUILD_OPTIONS.gcc16='c++ always-libgcc' PKG_BUILD_OPTIONS.llvm=tests \
        PKG_BUILD_OPTIONS.MesaLib='llvm x11 wayland' \
        EMBERBSD_MESA_GENERATORS="$work/mesa-generators" \
        USE_BUILTIN.pthread=yes H_PTHREAD=/usr/include/pthread.h \
        _MAKE="$work/host-make" "\$@"
MAKE
chmod +x "$work/host-make"
mkdir -p "$work/toolbase/gcc16/bin"
: > "$work/toolbase/gcc16/bin/cc"
chmod +x "$work/toolbase/gcc16/bin/cc"
run() {
    recipe=$1 conf=$2; shift 2
    MAKECONF="$work/$conf.conf" "$work/host-make" -C "$tree/$recipe" \
        -V 'compiler=${_GCC_PKGBASE}' -V 'use=${_USE_PKGSRC_GCC:tl}' \
        -V 'prefix=${_GCC_PREFIX}' -V 'runtime=${USE_PKGSRC_GCC_RUNTIME:tl}' \
        -V 'method=${BUILDLINK_DEPMETHOD.gcc16}' \
        -V 'deps=${DEPENDS} ${BUILD_DEPENDS} ${TOOL_DEPENDS}' \
        -V 'ldflags=${_GCC_LDFLAGS}' -V 'wrapcc=${_WRAP_EXTRA_ARGS.CC}' \
        -V 'wrapcxx=${_WRAP_EXTRA_ARGS.CXX}' -V 'wrappers=${WRAPPER_TARGETS}' \
        -V 'gccdeps=${BUILDLINK_API_DEPENDS.gcc16}' -V 'floor=${_GCC_REQD}' \
        -V 'python=${_PYTHON_VERSION}' -V 'platforms=${ONLY_FOR_PLATFORM}' \
        -V 'v3d=${PLIST.v3d:Uno}' -V 'meson=${MESON_ARGS}' -V 'fail=${PKG_FAIL_REASON}' "$@"
}
diagnostics() {
    log=$1 expected=${2:-}
    if grep -E 'warning:|no system rules|stopped making|^bmake.*(fatal|error)' "$log"; then
        echo "FAIL: unexpected make diagnostic in $log" >&2; return 1
    fi
    # Keep real host limitations visible; every other positive failure is fatal.
    # Negative cases allow only their named policy and the known patch-floor error.
    awk -v expected="$expected" '
        /^fail=/ {
            text=$0
            while (match(text, /"[^"]*"/)) {
                reason=substr(text, RSTART+1, RLENGTH-2)
                text=substr(text, RSTART+RLENGTH)
                if (reason ~ /^[^ ]+ requires a working dlopen\(\)\.$/ ||
                    reason ~ /^License conditions for [^ ]+ could not be evaluated$/ ||
                    reason ~ /^\[bsd.pkg.mk\] [^ ]+ uses X11, but \/usr\/X11R7 not found$/)
                    continue
                if (expected != "" && index(reason, expected)) continue
                if (expected == "requires GCC_REQD=16.2" && reason == "Unable to satisfy dependency: gcc>=16.2.0, newest pkgsrc version is 16.2.0") continue
                print "FAIL: unexpected package premise: " reason > "/dev/stderr"
                failed=1
            }
        }
        END { exit failed+0 }
    ' "$log"
}
selected() {
    name=$1 recipe=$2 conf=$3; shift 3
    run "$recipe" "$conf" "$@" > "$work/$name.log" 2>&1
    diagnostics "$work/$name.log"
    grep -qx 'compiler=gcc16' "$work/$name.log"
    grep -qx 'use=yes' "$work/$name.log"
    grep -qx 'prefix=/usr/pkg/gcc16/' "$work/$name.log"
    grep -qx 'runtime=no' "$work/$name.log"
    grep -qx 'method=full' "$work/$name.log"
    grep '^deps=.*gcc16>=16.2:../../lang/gcc16' "$work/$name.log" >/dev/null
    grep '^ldflags=.*-L/usr/pkg/gcc16/lib.*-Wl,-R/usr/pkg/gcc16/lib' "$work/$name.log" >/dev/null
    if grep -E 'gcc16-libs|specs.libgcc|The common tools.*(requires|supports)' "$work/$name.log"; then exit 1; fi
    echo "PASS: actual compiler/full-package/runtime selection $name"
}
# C-only and C++ consumers, then existing canonical family composition.
selected c-only devel/zlib tools
selected cxx textproc/icu tools
selected python lang/python315 tools
selected llvm lang/llvm tools
selected clang lang/clang tools
run devel/zlib tools \
    "GCCBASE=$work/toolbase/gcc16" "TOOLBASE=$work/toolbase" _GCC_VERSION=16.2.0 \
    > "$work/exact-version-floor.log" 2>&1
diagnostics "$work/exact-version-floor.log"
grep -qx 'floor=16.2' "$work/exact-version-floor.log"
echo 'PASS: package GCC 16.2.0 contributes the supported 16.2 compiler floor'
selected graphics graphics/MesaLib graphics
selected libdrm x11/libdrm graphics
grep "^platforms=.*NetBSD-11.\*-$arch" "$work/graphics.log" >/dev/null
grep "^platforms=.*NetBSD-11.\*-$arch" "$work/libdrm.log" >/dev/null
case "$arch" in
    aarch64) drivers=v3d,virgl,softpipe,llvmpipe,zink; v3d=yes ;;
    x86_64) drivers=iris,radeonsi,virgl,softpipe,llvmpipe,zink; v3d=no ;;
esac
grep "^meson=.*-Dgallium-drivers=$drivers " "$work/graphics.log" >/dev/null
grep -qx "v3d=$v3d" "$work/graphics.log"
selected media multimedia/ffmpeg9 media
selected same-floor devel/zlib tools GCC_REQD=16.2
selected cache-chain devel/zlib tools 'PKGSRC_COMPILER=ccache gcc'
selected distributed-chain devel/zlib tools 'PKGSRC_COMPILER=distcc gcc'
selected lower-recipe-floor devel/zlib tools 'GCC_REQD=12 16.2'
# Absence retains real dependency selection, without inventing executable paths.
run textproc/icu tools PKG_INFO=/usr/bin/false > "$work/missing-package.log" 2>&1
diagnostics "$work/missing-package.log"
grep '^deps=.*gcc16>=16.2:../../lang/gcc16' "$work/missing-package.log" >/dev/null
grep 'prefix=/usr/pkg/_GCC_SUBPREFIX_not_found/' "$work/missing-package.log" >/dev/null
echo 'PASS: missing installed compiler stays an unresolved real package dependency'
rejected() {
    name=$1 reason=$2; shift 2
    run devel/zlib tools "$@" > "$work/$name.log" 2>&1
    diagnostics "$work/$name.log" "$reason"
    grep -F "$reason" "$work/$name.log" >/dev/null
    echo "PASS: incompatible policy rejected $name"
}
rejected old-floor 'requires GCC_REQD=16.2' GCC_REQD=12
rejected patch-floor 'requires GCC_REQD=16.2' GCC_REQD=16.2.0
rejected other-compiler 'selected pkgsrc GCC 16.2' PKGSRC_COMPILER=clang
rejected native-compiler 'selected pkgsrc GCC 16.2' USE_NATIVE_GCC=yes
rejected package-optout 'selected pkgsrc GCC 16.2' USE_PKGSRC_GCC=no
rejected separate-runtime 'complete gcc16 runtime' USE_PKGSRC_GCC_RUNTIME=yes
rejected build-only 'full dependency' BUILDLINK_DEPMETHOD.gcc16=build
rejected foreign-prefix 'one final /usr/pkg prefix' LOCALBASE=/opt/pkg
rejected foreign-platform 'NetBSD 11/AArch64 or amd64 only' MACHINE_ARCH=earmv7hf
# Early profile cross guard only; actual cross metadata requires a target sysroot.
cat > "$work/cross.mk" <<MK
BSD_PKG_MK=yes
.include "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF"
MK
"$make" -r -m / -f "$work/cross.mk" OPSYS=NetBSD OS_VERSION=11.0 \
    MACHINE_ARCH="$arch" PREFIX=/usr/pkg LOCALBASE=/usr/pkg USE_CROSS_COMPILE=yes \
    -V '${PKG_FAIL_REASON}' > "$work/cross.log"
grep 'require native package builds' "$work/cross.log" >/dev/null
for recipe in lang/gcc16 math/mpfr math/mpcomplex devel/gtexinfo; do
    name=${recipe##*/}
    run "$recipe" bootstrap > "$work/bootstrap-$name.log" 2>&1
    diagnostics "$work/bootstrap-$name.log"
    grep -qx 'use=no' "$work/bootstrap-$name.log"
    if grep '^deps=.*gcc16[><=-].*:../../lang/gcc16' "$work/bootstrap-$name.log"; then exit 1; fi
    echo "PASS: native GCC12 bootstrap boundary $recipe"
done
run devel/zlib plain > "$work/plain.log" 2>&1
diagnostics "$work/plain.log"
grep -qx 'use=no' "$work/plain.log"
if grep '^deps=.*gcc16[><=-]' "$work/plain.log"; then exit 1; fi
# The real exporter, run by the caller, must include the unchanged profile bytes.
cmp "$root/profiles/common-build-tools/mk.conf" "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF"
cmp "$root/profiles/development-toolchain/mk.conf" "$tree/EMBERBSD-DEVELOPMENT-MK.CONF"
echo 'PASS: exported configuration, plain/native bootstrap boundaries; native runtime gate pending'
