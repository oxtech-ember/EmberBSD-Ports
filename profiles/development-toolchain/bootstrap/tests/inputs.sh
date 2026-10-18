#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the real bootstrap preflight without compiling GCC or target code.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
[ -f "$here/build.sh" ] || { echo 'FAIL: runtime bootstrap entry point is missing' >&2; exit 1; }
work=$(mktemp -d ${TMPDIR:-/tmp}/ember-gcc-runtime-inputs.XXXXXX)
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
    -v) echo "Thread model: ${FIXTURE_THREADS:-posix}" >&2;;
    -print-prog-name=*) echo "$(dirname "$(dirname "$0")")/libexec/${1#*=}";;
    -dM)
        cat >/dev/null
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
if [ "$1" = --version ]; then echo 'GNU readelf (NetBSD Binutils nb1) 2.42'; exit; fi
echo '  Class: ELF64'
echo '  OS/ABI: UNIX - NetBSD'
echo "  Machine:                           ${FIXTURE_MACHINE:-Advanced Micro Devices X86-64}"
EOF
cat > "$work/gmake" <<'EOF'
#!/bin/sh
case "$1" in --version) echo 'GNU Make 4.4.1';; *) exit 99;; esac
EOF
cat > "$work/binutil" <<'EOF'
#!/bin/sh
name=${0##*-}; [ "$name" != as ] || name=assembler
echo "GNU $name (NetBSD Binutils nb1) 2.42"
if [ "$name" = assembler ]; then
    triplet=${0##*/}; triplet=${triplet%-as}
    echo "This assembler was configured for a target of $triplet"
fi
EOF
chmod +x "$work/compiler" "$work/readelf" "$work/gmake"
chmod +x "$work/binutil"
for triplet in x86_64--netbsd aarch64--netbsd; do
    for tool in gcc g++; do cp "$work/compiler" "$work/kernel/toolchain/bin/$triplet-$tool"; done
    cp "$work/readelf" "$work/kernel/toolchain/bin/$triplet-readelf"
    for tool in ar as ld nm objcopy objdump ranlib strip; do
        cp "$work/binutil" "$work/kernel/toolchain/bin/$triplet-$tool"
    done
done
mkdir -p "$work/kernel/toolchain/libexec"
cp "$work/compiler" "$work/kernel/toolchain/libexec/cc1"
cp "$work/compiler" "$work/kernel/toolchain/libexec/cc1plus"
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
# An explicit existing POSIX compiler needs its own honest provenance mode.
external_run() {
    sh "$builder" --check --external-compiler --target "${target:-amd64}" "$work/pkgsrc" \
        "$work/gcc.tar.xz" "$work/kernel/toolchain" "$work/seed" "$work/math" "$work/output"
}
mv "$work/kernel/inputs.txt" "$work/kernel/inputs.saved"
external_run > "$work/external.plan"
grep -qx 'compiler_mode=external-posix' "$work/external.plan"
grep -qx 'support_target=libgcc-support' "$work/external.plan"
[ ! -e "$work/output" ]
external_reject() {
    if external_run > "$work/external-reject.log" 2>&1; then
        echo "FAIL: external mode accepted $1" >&2; exit 1
    fi
    [ ! -e "$work/output" ]
}
(FIXTURE_THREADS=single external_reject 'single-thread compiler')
(FIXTURE_VERSION=12.5.0 external_reject 'old compiler')
(FIXTURE_TRIPLET=aarch64--netbsd external_reject 'wrong compiler target')
(FIXTURE_MACHINE=AArch64 external_reject 'wrong seed architecture')
(EMBERBSD_SYSROOT_SOURCE=unknown external_reject 'unidentified seed')
mv "$work/kernel/toolchain/libexec/cc1plus" "$work/cc1plus.saved"
external_reject 'missing C++ frontend'
mv "$work/cc1plus.saved" "$work/kernel/toolchain/libexec/cc1plus"
(target=aarch64 FIXTURE_TRIPLET=aarch64--netbsd FIXTURE_MACHINE=AArch64 external_run) > "$work/external-aarch64.plan"
grep -qx 'triplet=aarch64--netbsd' "$work/external-aarch64.plan"
mv "$work/kernel/inputs.saved" "$work/kernel/inputs.txt"
# A resume preflight must validate the old input receipt and keep objects.
mkdir -p "$work/output/src" "$work/output/build/gcc" "$work/output/stage"
cp "$work/compiler" "$work/output/build/gcc/xgcc"
printf 'preserved frontend object\n' > "$work/output/build/gcc/frontend.o"
printf 'receipt-only input\n' > "$work/resume-input"
{
    printf 'scope=runtime-only-bootstrap\ntarget=amd64\ntriplet=x86_64--netbsd\nseed_source=%s\n' "$EMBERBSD_SYSROOT_SOURCE"
    printf 'kernel=%s\nsysroot=%s\nmath=%s\nhost_cc=cc\nhost_cxx=c++\nhost_cflags=-O2\nhost_cxxflags=-O2\n' \
        "$work/kernel/toolchain" "$(realpath "$work/seed")" "$work/math"
    shasum -a 256 "$work/gcc.tar.xz" "$recipe/distinfo" "$work/resume-input"
} > "$work/output/inputs.txt"
resume_check() {
    sh "$builder" --check --resume --target amd64 "$work/pkgsrc" "$work/gcc.tar.xz" \
        "$work/kernel/toolchain" "$work/seed" "$work/math" "$work/output"
}
resume_check > "$work/resume.plan"
grep -qx 'preserved frontend object' "$work/output/build/gcc/frontend.o"
mkdir -p "$work/output/build/x86_64--netbsd/libgcc"
printf 'stale configure\n' > "$work/output/build/gcc/Makefile"
printf 'empty nm selection\n' > "$work/output/build/gcc/config.cache"
printf 'broken generated nm\n' > "$work/output/build/gcc/nm"
printf 'preserved target object\n' > "$work/output/build/x86_64--netbsd/libgcc/div.o"
: > "$work/output/build/x86_64--netbsd/libgcc/libgcc.map"
: > "$work/output/build/x86_64--netbsd/libgcc/tmp-libgcc.map"
: > "$work/output/build/x86_64--netbsd/libgcc/libgcc.a"
(
    work=$work/output triplet=x86_64--netbsd
    fail() { echo "$*" >&2; exit 2; }
    . "$here/resume-state.sh"
    backup_resume
    [ ! -e "$work/build/gcc/nm" ] && [ ! -e "$work/build/gcc/config.cache" ]
    [ ! -e "$work/build/gcc/Makefile" ]
    [ ! -e "$work/build/$triplet/libgcc/libgcc.map" ]
    [ ! -e "$work/build/$triplet/libgcc/tmp-libgcc.map" ]
    [ ! -e "$work/build/$triplet/libgcc/libgcc.a" ]
    [ -f "$resume_backup/build/gcc/nm" ]
    [ -f "$resume_backup/build/$triplet/libgcc/tmp-libgcc.map" ]
    grep -qx 'preserved target object' "$work/build/$triplet/libgcc/div.o"
    grep -qx 'preserved frontend object' "$work/build/gcc/frontend.o"
    grep -q '^resume_prior_inputs_sha256=' "$work/inputs.txt"
)
printf 'changed receipt input\n' >> "$work/resume-input"
if resume_check > "$work/resume-reject.log" 2>&1; then echo 'FAIL: changed resume inputs accepted' >&2; exit 1; fi
printf 'receipt-only input\n' > "$work/resume-input"
if (HOST_CFLAGS=-O3 resume_check) > "$work/resume-reject.log" 2>&1; then echo 'FAIL: changed host flags accepted' >&2; exit 1; fi
if (FIXTURE_THREADS=single resume_check) > "$work/resume-reject.log" 2>&1; then echo 'FAIL: single-thread frontend accepted' >&2; exit 1; fi
printf 'partial installation\n' > "$work/output/stage/untracked"
if resume_check > "$work/resume-reject.log" 2>&1; then echo 'FAIL: partial stage accepted' >&2; exit 1; fi
# Target-only recovery accepts that partial stage only with a complete frontend
# and the preceding explicit GNU target-binutils provenance.
runtime_check() {
    sh "$builder" --check --resume-runtime "$@" --target amd64 "$work/pkgsrc" "$work/gcc.tar.xz" \
        "$work/kernel/toolchain" "$work/seed" "$work/math" "$work/output"
}
if runtime_check > "$work/resume-reject.log" 2>&1; then echo 'FAIL: missing binutils receipt accepted' >&2; exit 1; fi
printf 'target_binutils=audited-kernel-prefix\n' >> "$work/output/inputs.txt"
for state in Makefile config.cache config.status config.log auto-host.h configargs.h; do
    printf 'completed frontend state\n' > "$work/output/build/gcc/$state"
done
for driver in cc1 cc1plus; do cp "$work/compiler" "$work/output/build/gcc/$driver"; done
runtime_check > "$work/runtime-resume.plan"
grep -qx 'partial installation' "$work/output/stage/untracked"
if (FIXTURE_THREADS=single runtime_check) > "$work/resume-reject.log" 2>&1; then echo 'FAIL: runtime recovery accepted single-thread frontend' >&2; exit 1; fi
if (HOST_CFLAGS=-O3 runtime_check) > "$work/resume-reject.log" 2>&1; then echo 'FAIL: runtime recovery accepted changed host flags' >&2; exit 1; fi
rm "$work/output/stage/untracked"
printf 'completed stage\n' > "$work/output/build-success"
if resume_check > "$work/resume-reject.log" 2>&1; then echo 'FAIL: completed stage accepted for resume' >&2; exit 1; fi
if runtime_check > "$work/resume-reject.log" 2>&1; then echo 'FAIL: completed stage accepted for runtime recovery' >&2; exit 1; fi
# An explicit additional-library request may reuse an unchanged completed
# stage. These are preflight fixtures, not compiler or target runtime outputs.
printf 'runtime-only-bootstrap\n' > "$work/output/build-success"
printf 'completed inventory fixture\n' > "$work/output/stage/recorded"
(cd "$work/output/stage" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort) > "$work/output/stage.sha256"
: > "$work/output/stage.symlinks"
runtime_check --with-libgomp --with-libatomic > "$work/runtime-extension.plan"
grep -qx 'runtime_libraries=libgcc,libstdc++,libgomp,libatomic' "$work/runtime-extension.plan"
grep -qx 'completed inventory fixture' "$work/output/stage/recorded"
grep -qx runtime-only-bootstrap "$work/output/build-success"
printf 'unrecorded fixture\n' > "$work/output/stage/additional"
if runtime_check --with-libgomp > "$work/extension-reject.log" 2>&1; then echo 'FAIL: extended stage accepted an unrecorded file' >&2; exit 1; fi
grep -qx 'Completed-stage file inventory or hashes changed.' "$work/extension-reject.log"
rm -rf "$work/output"
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
