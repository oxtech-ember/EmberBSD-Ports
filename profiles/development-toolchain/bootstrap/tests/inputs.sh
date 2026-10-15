#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the real bootstrap preflight without compiling GCC or target code.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
[ -f "$here/build.sh" ] || { echo 'FAIL: runtime bootstrap entry point is missing' >&2; exit 1; }
work=$(mktemp -d /tmp/ember-gcc-runtime-inputs.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/profile/bootstrap" "$work/profile/cross" "$work/pkgsrc/lang/gcc16/patches" \
    "$work/kernel/toolchain/bin" "$work/seed/usr/include" "$work/seed/usr/lib" \
    "$work/math/include" "$work/math/lib"
# Copy the implementation into a small independent source-manifest fixture.
cp "$here"/*.sh "$work/profile/bootstrap/"
builder=$work/profile/bootstrap/build.sh
recipe=$work/pkgsrc/lang/gcc16
printf 'audited GCC archive fixture\n' > "$work/gcc.tar.xz"
hash=$(shasum -a 256 "$work/gcc.tar.xz" | awk '{print $1}')
printf 'gcc\t16.2.0\thttps://example.invalid/gcc.tar.xz\t%s\n' "$hash" > "$work/profile/sources.tsv"
printf 'modules repair fixture\n' > "$recipe/patches/patch-gcc_cp_module.cc"
patch_hash=$(shasum -a 1 "$recipe/patches/patch-gcc_cp_module.cc" | awk '{print $1}')
printf 'SHA1 (patch-gcc_cp_module.cc) = %s\n' "$patch_hash" > "$recipe/distinfo"
recipe_hash=$(shasum -a 256 "$recipe/distinfo" | awk '{print $1}')
printf 'mode=kernel\n%s  gcc.tar.xz\n%s  lang/gcc16/distinfo\n' "$hash" "$recipe_hash" > "$work/kernel/inputs.txt"
cat > "$recipe/Makefile" <<'EOF'
CONFIGURE_ARGS+= --disable-libssp
SUBST_SED.libstdc= -e 's,libtool_VERSION=6:,libtool_VERSION=7:,g'
EOF
for header in stddef.h stdio.h pthread.h math.h; do
    printf 'target header fixture\n' > "$work/seed/usr/include/$header"
done
for library in libc.so.12 libpthread.so.1 libm.so.0 crt0.o; do
    printf 'target ELF fixture\n' > "$work/seed/usr/lib/$library"
done
for library in gmp mpfr mpc; do
    printf 'host archive fixture\n' > "$work/math/lib/lib$library.a"
done
cat > "$work/math/include/gmp.h" <<'EOF'
#define __GNU_MP_VERSION 6
#define __GNU_MP_VERSION_MINOR 3
#define __GNU_MP_VERSION_PATCHLEVEL 0
EOF
cat > "$work/math/include/mpfr.h" <<'EOF'
#define MPFR_VERSION_MAJOR 4
#define MPFR_VERSION_MINOR 2
#define MPFR_VERSION_PATCHLEVEL 2
EOF
cat > "$work/math/include/mpc.h" <<'EOF'
#define MPC_VERSION_MAJOR 1
#define MPC_VERSION_MINOR 4
#define MPC_VERSION_PATCHLEVEL 1
EOF
cat > "$work/compiler" <<'EOF'
#!/bin/sh
case "$1" in
    -dumpmachine) echo "${FIXTURE_TRIPLET:-x86_64--netbsd}";;
    -dumpfullversion) echo "${FIXTURE_VERSION:-16.2.0}";;
    --version) echo 'gcc (GCC) 16.2.0';;
    -dM)
        echo '#define __GNUC__ 16'
        echo '#define __NetBSD__ 1'
        echo '#define __SIZEOF_POINTER__ 8'
        case "${FIXTURE_TRIPLET:-x86_64--netbsd}" in
            x86_64--netbsd) echo '#define __x86_64__ 1';;
            aarch64--netbsd) echo '#define __aarch64__ 1';;
        esac;;
    *) echo 'Unexpected compiler operation in preflight' >&2; exit 99;;
esac
EOF
cat > "$work/readelf" <<'EOF'
#!/bin/sh
echo '  Class: ELF64'
echo '  OS/ABI: UNIX - NetBSD'
echo "  Machine:                           ${FIXTURE_MACHINE:-Advanced Micro Devices X86-64}"
EOF
cat > "$work/gmake" <<'EOF'
#!/bin/sh
case "$1" in --version) echo 'GNU Make 4.4.1';; *) exit 99;; esac
EOF
chmod +x "$work/compiler" "$work/readelf" "$work/gmake"
for triplet in x86_64--netbsd aarch64--netbsd; do
    for tool in gcc g++; do cp "$work/compiler" "$work/kernel/toolchain/bin/$triplet-$tool"; done
    cp "$work/readelf" "$work/kernel/toolchain/bin/$triplet-readelf"
    for tool in ar as ld nm objcopy objdump ranlib strip; do
        cp "$work/gmake" "$work/kernel/toolchain/bin/$triplet-$tool"
    done
done
export GNU_MAKE=$work/gmake
export EMBERBSD_SYSROOT_SOURCE=0123456789012345678901234567890123456789
run() {
    sh "$builder" --check --target "${target:-amd64}" "$work/pkgsrc" \
        "$work/gcc.tar.xz" "$work/kernel/toolchain" "$work/seed" "$work/math" "$work/output"
}
reject() {
    if run > "$work/check.log" 2>&1; then
        echo "FAIL: accepted $1" >&2; exit 1
    fi
    [ ! -e "$work/output" ] || { echo 'FAIL: rejected input created work directory' >&2; exit 1; }
}
if sh "$builder" > "$work/usage.log" 2>&1; then echo 'FAIL: missing arguments accepted' >&2; exit 1; fi
run > "$work/amd64.plan"
grep -qx 'triplet=x86_64--netbsd' "$work/amd64.plan"
grep -qx 'abi=libstdc++.so.7' "$work/amd64.plan"
grep -qx 'target_flags=-O2 -march=nocona -mtune=nocona -mfpmath=sse' "$work/amd64.plan"
[ ! -e "$work/output" ]
(target=aarch64 FIXTURE_TRIPLET=aarch64--netbsd FIXTURE_MACHINE=AArch64 run) > "$work/aarch64.plan"
grep -qx 'triplet=aarch64--netbsd' "$work/aarch64.plan"
grep -qx 'target_flags=-O2' "$work/aarch64.plan"
(target=riscv64 reject 'unsupported architecture')
(FIXTURE_TRIPLET=aarch64--netbsd reject 'wrong compiler triplet')
(FIXTURE_VERSION=12.5.0 reject 'old compiler')
(FIXTURE_MACHINE=AArch64 reject 'wrong seed ELF architecture')
(CROSS_JOBS=0 reject 'zero workers')
(EMBERBSD_SYSROOT_SOURCE=unknown reject 'missing seed provenance')
mv "$work/kernel/inputs.txt" "$work/kernel/inputs.saved"
reject 'compiler without the audited kernel build receipt'
mv "$work/kernel/inputs.saved" "$work/kernel/inputs.txt"
cp "$recipe/Makefile" "$work/recipe.saved"
sed 's/libtool_VERSION=7:/libtool_VERSION=9:/' "$work/recipe.saved" > "$recipe/Makefile"
reject 'divergent pkgsrc C++ ABI'
cp "$work/recipe.saved" "$recipe/Makefile"
printf 'modified patch\n' >> "$recipe/patches/patch-gcc_cp_module.cc"
reject 'changed source patch'
printf 'PASS: runtime bootstrap architecture, ABI and preflight guards\n'
