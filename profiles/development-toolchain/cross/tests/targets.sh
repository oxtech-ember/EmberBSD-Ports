#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted host fixtures for cross-target selection.
# These fixtures inspect orchestration. They do not compile target programs.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d /tmp/ember-gcc-targets.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
unset EMBER_HOST_MATH_PREFIX
export CROSS_JOBS=1

reject() {
    script=$1 expected=$2; shift 2
    status=0
    sh "$here/$script" "$@" > "$work/reject.log" 2>&1 || status=$?
    [ "$status" -eq "${REJECT_STATUS:-2}" ] && grep -Fq "$expected" "$work/reject.log" || {
        cat "$work/reject.log" >&2
        echo "Wrong rejection from $script; expected: $expected" >&2
        exit 1
    }
    [ ! -e "$work/new" ]
}

# A misspelled or repeated target must fail before creating any output.
for script in build.sh compile-tests.sh test-inputs.sh tests/split-dwarf.sh run-target.sh; do
    reject "$script" 'Unsupported target:' --target riscv64
    reject "$script" 'Usage:' --target
    reject "$script" 'Usage:' --target ''
    reject "$script" 'Usage:' --target amd64 --target aarch64
done
reject build.sh 'Usage:' --kernel --kernel

mkdir -p "$work/tools/bin" "$work/sysroot/usr/include"
touch "$work/sysroot/usr/include/stddef.h" "$work/archive"
printf '#!/bin/sh\nexit 0\n' > "$work/tools/bin/nbgmake"
chmod +x "$work/tools/bin/nbgmake"
for pair in aarch64:aarch64--netbsd amd64:x86_64--netbsd; do
    target=${pair%:*} triplet=${pair#*:}
    for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
        cp "$work/tools/bin/nbgmake" "$work/tools/bin/$triplet-$tool"
    done
    (REJECT_STATUS=1 reject build.sh 'GCC archive SHA256 mismatch.' --target "$target" --kernel \
        "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new")
    reject build.sh 'The sysroot must contain the selected target GCC16 package.' \
        --target "$target" "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/new"
done

# An amd64 invocation must not inherit old target binutils from the OS TOOLDIR.
mkdir -p "$work/sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0" \
    "$work/sysroot/usr/pkg/gcc16/include/c++"
touch "$work/sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o"
reject build.sh 'Selected target GCC16 C++ headers missing.' --target aarch64 \
    "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/new"
reject build.sh 'The sysroot must contain the selected target GCC16 package.' --target amd64 \
    "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/new"
rm "$work/tools/bin/x86_64--netbsd-as"
(REJECT_STATUS=1 reject build.sh 'GCC archive SHA256 mismatch.' --kernel --target amd64 \
    "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new"
)

# Compiler fixtures replace the expensive external compiler boundary only.
# They record the real script's flags and create its expected output files.
cat > "$work/compiler" <<'EOF'
#!/bin/sh
set -eu
case "$1" in
    -dumpfullversion) echo 16.2.0; exit;;
    -dumpmachine) echo "$FIXTURE_TRIPLET"; exit;;
esac
printf '%s\n' "$@" >> "$FIXTURE_LOG"
out=
while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then out=$2; shift; fi
    shift
done
if [ -n "$out" ]; then
    : > "$out"
    printf fixture > "${out%.o}.dwo"
fi
EOF
cat > "$work/readelf" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' "$@" >> "$FIXTURE_LOG"
case "$1" in
    --debug-dump=info) echo 'DW_UT_skeleton DW_UT_split_compile';;
    --debug-dump=str-offsets) echo 'split_record';;
esac
EOF
chmod +x "$work/compiler" "$work/readelf"
mkdir "$work/host-bin"
cat > "$work/host-bin/uname" <<'EOF'
#!/bin/sh
case "$1" in -s) echo NetBSD;; -p) echo "$FIXTURE_PROCESSOR";; *) exit 1;; esac
EOF
chmod +x "$work/host-bin/uname"
for pair in default:aarch64--netbsd aarch64:aarch64--netbsd amd64:x86_64--netbsd; do
    target=${pair%:*} triplet=${pair#*:}
    prefix=$work/prefix-$target
    mkdir -p "$prefix/bin" "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0" \
        "$work/sysroot/usr/pkg/gcc16/include/c++/$triplet"
    touch "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o"
    touch "$work/sysroot/usr/pkg/gcc16/lib/libstdc++.so.7" "$work/sysroot/usr/pkg/gcc16/lib/libgcc_s.so.1"
    cp "$work/compiler" "$prefix/bin/$triplet-gcc"
    cp "$work/compiler" "$prefix/bin/$triplet-g++"
    cp "$work/readelf" "$prefix/bin/$triplet-readelf"
    FIXTURE_LOG=$work/$target.log FIXTURE_TRIPLET=$triplet
    export FIXTURE_LOG FIXTURE_TRIPLET
    : > "$FIXTURE_LOG"
    mv "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o" \
        "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.saved"
    selected_target=$target
    [ "$selected_target" != default ] || selected_target=aarch64
    reject compile-tests.sh 'Selected target GCC16 runtime missing.' --target "$selected_target" \
        "$prefix" "$work/sysroot" "$work/new"
    mv "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.saved" \
        "$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/crtbegin.o"
    set --
    [ "$target" = default ] || set -- --target "$target"
    sh "$here/compile-tests.sh" "$@" "$prefix" "$work/sysroot" "$work/tests-$target"
    grep -Fxq -- "-B$work/sysroot/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0/" "$FIXTURE_LOG"
    grep -Fxq -- "$work/sysroot/usr/pkg/gcc16/include/c++/$triplet" "$FIXTURE_LOG"
    case "$target" in amd64) foreign=aarch64--netbsd;; *) foreign=x86_64--netbsd;; esac
    if grep -Fq "$foreign" "$FIXTURE_LOG"; then echo 'Foreign target flags.' >&2; exit 1; fi
    test -f "$work/tests-$target/boundary"
    [ "$(cat "$work/tests-$target/target.txt")" = "$selected_target" ]
    test -f "$work/tests-$target/target-options.sh"
    (FIXTURE_TRIPLET=$foreign reject compile-tests.sh 'Selected target GCC16 compiler mismatch.' \
        --target "$selected_target" "$prefix" "$work/sysroot" "$work/new")
    case "$selected_target" in aarch64) FIXTURE_PROCESSOR=aarch64;; amd64) FIXTURE_PROCESSOR=x86_64;; esac
    export FIXTURE_PROCESSOR
    (PATH=$work/host-bin:$PATH LD_LIBRARY_PATH=guard reject run-target.sh \
        'Remove loader overrides.' --target "$selected_target" "$work/tests-$target")
    printf 'wrong-target\n' > "$work/tests-$target/target.txt"
    (PATH=$work/host-bin:$PATH reject run-target.sh 'Compiled test target mismatch.' \
        --target "$selected_target" "$work/tests-$target")
    printf '%s\n' "$selected_target" > "$work/tests-$target/target.txt"
    sh "$here/tests/split-dwarf.sh" "$@" "$prefix" "$work/split-$target"
done
echo 'PASS: target rejection, selected runtime/binutils, compile flags and split-DWARF dispatch (host fixtures)'
