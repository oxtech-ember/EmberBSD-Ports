#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), metadata fixtures; no compiler acceptance claim.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
helper=$root/recipes/lang/clang/files/cross-gcc-config.sh
prefix=$work/sysroot/usr/pkg/gcc16
private=$prefix/lib/gcc/aarch64--netbsd/16.2.0
mkdir -p "$private" "$prefix/lib" "$prefix/bin" \
    "$prefix/include/c++/aarch64--netbsd" "$prefix/include/c++/backward"
touch "$prefix/bin/gcc"
for name in crtbegin.o crtbeginS.o crtend.o crtendS.o libgcc.a; do touch "$private/$name"; done
for name in libgcc_s.so.1 libstdc++.so; do touch "$prefix/lib/$name"; done
FIXTURE_PREFIX=$prefix; export FIXTURE_PREFIX
cat > "$work/gcc" <<'GCC'
#!/bin/sh
set -eu
for arg do
    case "$arg" in
        -dumpfullversion) echo "${FIXTURE_GCC_VERSION:-16.2.0}"; exit ;;
        -dumpmachine) echo aarch64--netbsd; exit ;;
        -print-file-name=*)
            name=${arg#*=}
            case "$name" in
                crt*.o|libgcc.a) echo "$FIXTURE_PREFIX/lib/gcc/aarch64--netbsd/16.2.0/$name" ;;
                *) echo "$FIXTURE_PREFIX/lib/$name" ;;
            esac
            exit ;;
    esac
done
printf '#include <...> search starts here:\n %s\n %s\n %s\nEnd of search list.\n' \
    "$FIXTURE_PREFIX/include/c++" "$FIXTURE_PREFIX/include/c++/aarch64--netbsd" \
    "${FIXTURE_LAST_INCLUDE:-$FIXTURE_PREFIX/include/c++/backward}" >&2
GCC
cat > "$work/llvm-config" <<'LLVM'
#!/bin/sh
case "$1" in
    --version) echo "${FIXTURE_LLVM_VERSION:-23.1.2}" ;;
    --host-target) echo "${FIXTURE_LLVM_TARGET:-aarch64-unknown-netbsd}" ;;
    *) exit 1 ;;
esac
LLVM
chmod +x "$work/gcc" "$work/llvm-config"
run() { sh "$helper" "$work/gcc" "$work/llvm-config" "$work/sysroot" /usr/pkg/gcc16 "$work/$1"; }
run accepted
cfg=$work/accepted/aarch64-unknown-netbsd.cfg
[ "$(grep -c '^-stdlib++-isystem/usr/pkg/gcc16/include/c++' "$cfg")" = 3 ]
grep -q '^-B/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/$' "$cfg"
! grep -Fq "$work" "$cfg"
if run accepted > "$work/existing.log" 2>&1; then exit 1; fi
if (export FIXTURE_GCC_VERSION=12.5.0; run old-gcc) > "$work/old-gcc.log" 2>&1; then exit 1; fi
if (export FIXTURE_LLVM_VERSION=22.1.0; run old-llvm) > "$work/old-llvm.log" 2>&1; then exit 1; fi
if (export FIXTURE_LLVM_TARGET=aarch64-unknown-linux-gnu; run linux) > "$work/linux.log" 2>&1; then exit 1; fi
if (export FIXTURE_LLVM_TARGET=aarch64-unknown-netbsd-eabi; run abi) > "$work/abi.log" 2>&1; then exit 1; fi
if (export FIXTURE_LAST_INCLUDE="$prefix/include/c++"; run duplicate) > "$work/duplicate.log" 2>&1; then exit 1; fi
mv "$prefix/lib/libstdc++.so" "$work/foreign-libstdc++.so"
ln -s "$work/foreign-libstdc++.so" "$prefix/lib/libstdc++.so"
if run escape > "$work/escape.log" 2>&1; then exit 1; fi
rm "$prefix/lib/libstdc++.so"
if run missing > "$work/missing.log" 2>&1; then exit 1; fi
for name in old-gcc old-llvm linux abi duplicate escape missing; do
    [ ! -e "$work/$name" ]
    grep -q '^Invalid cross GCC metadata:' "$work/$name.log"
done
grep -q 'expected GCC 16.2.0' "$work/old-gcc.log"
grep -q 'expected LLVM 23.1.2' "$work/old-llvm.log"
grep -q 'unsupported LLVM target' "$work/linux.log"
grep -q 'target ABI mismatch' "$work/abi.log"
grep -q 'duplicate C++ include directory' "$work/duplicate.log"
grep -q 'outside selected GCC directory' "$work/escape.log"
grep -q 'missing libstdc++.so' "$work/missing.log"
echo 'PASS: cross GCC metadata contracts (fixtures, not compiler execution)'
