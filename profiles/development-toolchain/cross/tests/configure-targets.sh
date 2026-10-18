#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cross-GCC configure-boundary host fixture.
# Stop before building GCC. Assert the real recipe's configuration and layout.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d /tmp/ember-gcc-configure.XXXXXXXX)
work=$(CDPATH= cd -- "$work" && pwd -P)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
unset EMBER_HOST_MATH_PREFIX
mkdir -p "$work/profile/cross/tests" "$work/profile/cross/patches" \
    "$work/pkgsrc/lang/gcc16/patches" \
    "$work/math/include" "$work/math/lib" "$work/source" "$work/tools/bin" \
    "$work/sysroot/usr/include" "$work/sysroot/usr/pkg/gcc16/include/c++"
cp "$here/build.sh" "$here/target-options.sh" "$work/profile/cross/"
cp "$here/build-binutils.sh" "$work/profile/cross/"
cp "$here/test-inputs.sh" "$here/host-math.sh" "$here/host-sources.tsv" "$work/profile/cross/"
cp "$here/tests/host-gmp.c" "$work/profile/cross/tests/"
cp "$here/patches/gmp-t-rand-varargs.patch" "$work/profile/cross/patches/"
cat > "$work/profile/cross/build-binutils.sh" <<'EOF'
#!/bin/sh
set -eu
usage() { exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
kernel_allowed=no
. "$here/target-options.sh"
[ "$#" -eq 1 ] || usage
printf '%s\t%s\n' "$target" "$1" >> "$FIXTURE_BINUTILS_ARGS"
mkdir -p "$1/prefix/bin" "$1/prefix/$triplet/lib/ldscripts"
for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
    cp "$FIXTURE_TOOLS/bin/$triplet-$tool" "$1/prefix/bin/"
done
printf 'target=%s\ntriplet=%s\nfixture Ports Binutils 2.47\n' \
    "$target" "$triplet" > "$1/inputs.txt"
printf 'fixture linker script\n' > "$1/prefix/$triplet/lib/ldscripts/elf.x"
EOF
chmod +x "$work/profile/cross/build-binutils.sh"
for library in gmp mpfr mpc; do : > "$work/math/lib/lib$library.a"; done
printf '#define __GNU_MP_VERSION 6\n#define __GNU_MP_VERSION_MINOR 3\n#define __GNU_MP_VERSION_PATCHLEVEL 0\n' > "$work/math/include/gmp.h"
printf '#define MPFR_VERSION_MAJOR 4\n#define MPFR_VERSION_MINOR 2\n#define MPFR_VERSION_PATCHLEVEL 2\n' > "$work/math/include/mpfr.h"
printf '#define MPC_VERSION_MAJOR 1\n#define MPC_VERSION_MINOR 4\n#define MPC_VERSION_PATCHLEVEL 1\n' > "$work/math/include/mpc.h"
cat > "$work/host-cc" <<'EOF'
#!/bin/sh
set -eu
case "$1" in
    --version) echo 'fixture GCC 16 host compiler'; exit;;
    -dumpfullversion) echo "${FIXTURE_GCC_VERSION:-16.2.0}"; exit;;
    -dumpmachine) echo fixture-host; exit;;
esac
while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then
        printf '#!/bin/sh\nexit 0\n' > "$2"
        chmod +x "$2"
        exit
    fi
    shift
done
exit 1
EOF
cat > "$work/source/configure" <<'EOF'
#!/bin/sh
printf '%s\n' "$@" > "$FIXTURE_CONFIGURE"
printf '%s\n' "CPPFLAGS=$CPPFLAGS" "CFLAGS=$CFLAGS" "CXXFLAGS=$CXXFLAGS" "LDFLAGS=$LDFLAGS" > "$FIXTURE_CONFIGURE.flags"
exit 97
EOF
chmod +x "$work/source/configure" "$work/host-cc"
HOST_CC=$work/host-cc HOST_CXX=$work/host-cc
export HOST_CC HOST_CXX
mkdir "$work/host-bin"
cp "$work/host-cc" "$work/host-bin/gcc-16"
cp "$work/host-cc" "$work/host-bin/g++-16"
cp "$work/host-cc" "$work/host-bin/cc"
cp "$work/host-cc" "$work/host-bin/c++"
printf 'before\n' > "$work/source/fixture"
cat > "$work/pkgsrc/lang/gcc16/patches/patch-gcc_cp_module.cc" <<'EOF'
--- fixture.orig
+++ fixture
@@ -1 +1 @@
-before
+after
EOF
digest=$(shasum -a 1 "$work/pkgsrc/lang/gcc16/patches/patch-gcc_cp_module.cc" | awk '{print $1}')
printf 'SHA1 (patch-gcc_cp_module.cc) = %s\n' "$digest" > "$work/pkgsrc/lang/gcc16/distinfo"
tar -cf "$work/gcc.tar" -C "$work" source
digest=$(shasum -a 256 "$work/gcc.tar" | awk '{print $1}')
printf 'gcc\t16.2.0\tfixture\t%s\n' "$digest" > "$work/profile/sources.tsv"
printf '#!/bin/sh\necho fixture-tool\n' > "$work/tools/bin/nbgmake"
chmod +x "$work/tools/bin/nbgmake"
for pair in default:aarch64--netbsd aarch64:aarch64--netbsd amd64:x86_64--netbsd; do
    target=${pair%:*} triplet=${pair#*:}
    mkdir -p "$work/tools/$triplet/lib/ldscripts"
    printf 'fixture linker script\n' > "$work/tools/$triplet/lib/ldscripts/elf.x"
    for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
        cp "$work/tools/bin/nbgmake" "$work/tools/bin/$triplet-$tool"
    done
    mkdir -p "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0" \
        "$work/sysroot/usr/pkg/gcc16/include/c++/$triplet"
    touch "$work/sysroot/usr/include/stddef.h" \
        "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o"
    if [ "$target" != default ]; then
        sh "$work/profile/cross/test-inputs.sh" --target "$target" \
            "$work/pkgsrc" "$work/gcc.tar" "$work/sysroot" "$work/tools" "$work/math"
    fi
    if [ "$target" = default ]; then
        status=0
        FIXTURE_GCC_VERSION=14.2.0 HOST_CC=$work/host-cc HOST_CXX=$work/host-cc \
            CROSS_JOBS=1 sh "$work/profile/cross/build.sh" --kernel \
            "$work/pkgsrc" "$work/gcc.tar" "$work/tools" "$work/math" \
            "$work/rejected-host-compiler" > "$work/rejected-host-compiler.log" 2>&1 || status=$?
        [ "$status" -eq 2 ] || { cat "$work/rejected-host-compiler.log" >&2; exit 1; }
        grep -Fq 'GCC 16 host compiler required' "$work/rejected-host-compiler.log"
        test ! -e "$work/rejected-host-compiler"
    fi
    for mode in applications kernel; do
        output=$work/$target-$mode
        set --
        selected_target=$target
        if [ "$target" = default ]; then selected_target=aarch64; else set -- --target "$target"; fi
        if [ "$mode" = kernel ]; then set -- "$@" --kernel; fi
        set -- "$@" "$work/pkgsrc" "$work/gcc.tar"
        if [ "$mode" = applications ]; then set -- "$@" "$work/sysroot"; fi
        status=0
        if [ "$target" = default ] && [ "$mode" = applications ]; then
            env -u HOST_CC -u HOST_CXX PATH="$work/host-bin:$PATH" \
                CROSS_JOBS=1 HOST_CPPFLAGS="-isysroot /fixture/sdk" \
                HOST_LDFLAGS="-isysroot /fixture/link-sdk" \
                FIXTURE_CONFIGURE=$work/configure.txt FIXTURE_TOOLS=$work/tools \
                FIXTURE_BINUTILS_ARGS=$work/binutils.args \
                sh "$work/profile/cross/build.sh" "$@" "$work/tools" "$work/math" "$output" \
                > "$work/result.log" 2>&1 || status=$?
        else
            HOST_CC=$work/host-cc HOST_CXX=$work/host-cc CROSS_JOBS=1 \
                HOST_CPPFLAGS="-isysroot /fixture/sdk" HOST_LDFLAGS="-isysroot /fixture/link-sdk" \
                FIXTURE_CONFIGURE=$work/configure.txt FIXTURE_TOOLS=$work/tools \
                FIXTURE_BINUTILS_ARGS=$work/binutils.args \
                sh "$work/profile/cross/build.sh" "$@" "$work/tools" "$work/math" "$output" \
                > "$work/result.log" 2>&1 || status=$?
        fi
        [ "$status" -eq 97 ] || { cat "$work/result.log" >&2; exit 1; }
        grep -Fxq 'CPPFLAGS=-isysroot /fixture/sdk' "$work/configure.txt.flags"
        grep -Fxq 'CFLAGS=-O2 -isysroot /fixture/sdk' "$work/configure.txt.flags"
        grep -Fxq 'CXXFLAGS=-O2 -isysroot /fixture/sdk' "$work/configure.txt.flags"
        grep -Fxq 'LDFLAGS=-isysroot /fixture/link-sdk' "$work/configure.txt.flags"
        grep -Fxq -- "--target=$triplet" "$work/configure.txt"
        grep -Fxq -- "--with-as=$output/toolchain/bin/$triplet-as" "$work/configure.txt"
        grep -Fxq -- "--with-ld=$output/toolchain/bin/$triplet-ld" "$work/configure.txt"
        grep -Fxq "target=$selected_target" "$output/inputs.txt"
        grep -Fxq "triplet=$triplet" "$output/inputs.txt"
        if [ "$target" = default ] && [ "$mode" = applications ]; then
            grep -Fxq 'host_cc=gcc-16' "$output/inputs.txt"
            grep -Fxq 'host_cxx=g++-16' "$output/inputs.txt"
        fi
        grep -Fxq "target=$selected_target" "$output/binutils/inputs.txt"
        grep -Fxq "triplet=$triplet" "$output/binutils/inputs.txt"
        grep -Fxq 'fixture Ports Binutils 2.47' "$output/inputs.txt"
        awk -F '\t' -v target="$selected_target" -v path="$output/binutils" \
            '$1 == target && $2 == path { found = 1 } END { exit !found }' \
            "$work/binutils.args"
        test -x "$output/toolchain/bin/$triplet-as"
        test "$(readlink "$output/toolchain/$triplet/bin/objcopy")" = "../../bin/$triplet-objcopy"
        if [ "$mode" = kernel ]; then
            grep -Fxq -- --without-headers "$work/configure.txt"
            grep -Fxq -- --disable-shared "$work/configure.txt"
            grep -Fxq -- --disable-threads "$work/configure.txt"
            if grep -q -- --with-sysroot "$work/configure.txt"; then exit 1; fi
        else
            grep -Fxq -- "--with-sysroot=$work/sysroot" "$work/configure.txt"
            if grep -q -- --without-headers "$work/configure.txt"; then exit 1; fi
        fi
        case "$target" in amd64) foreign=aarch64--netbsd;; *) foreign=x86_64--netbsd;; esac
        if grep -Fq "$foreign" "$work/configure.txt"; then exit 1; fi
        test ! -e "$output/toolchain/bin/$foreign-as"
    done
done
echo 'PASS: both target triplets, binutils layout and application/kernel configure modes (host fixtures)'
