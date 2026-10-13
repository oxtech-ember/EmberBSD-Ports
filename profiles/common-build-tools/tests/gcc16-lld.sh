#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), explicit non-LTO GCC16/LLD23 ELF checks.
set -eu
LC_ALL=C
export LC_ALL
[ "$#" = 1 ] || {
    echo 'Usage: CC=... LLD=... READELF=... SYSROOT=... gcc16-lld.sh NEW_OUTPUT' >&2
    exit 2
}
: "${CC:?Set the absolute GCC16 driver path}"
: "${LLD:?Set the absolute native LLD23 path}"
: "${READELF:?Set the absolute native ELF reader path}"
: "${SYSROOT:?Set the EmberBSD 11 AArch64 sysroot path}"
# GCC specs and comma-separated linker arguments require simple paths.
for value in "$CC" "${CXX:-$CC}" "$LLD" "$READELF" "$SYSROOT" "$1"; do
    case "$value" in
        /*) ;;
        *) echo 'Use absolute paths' >&2; exit 2 ;;
    esac
    case "$value" in
        *[!a-zA-Z0-9_./+-]*) echo 'Use paths without spaces or metacharacters' >&2; exit 2 ;;
    esac
done
for tool in "$CC" "${CXX:-$CC}" "$LLD" "$READELF"; do
    [ -x "$tool" ] || { echo "Missing executable: $tool" >&2; exit 2; }
done
sysroot=$(CDPATH= cd -- "$SYSROOT" && pwd -P)
[ ! -e "$1" ] && [ ! -L "$1" ] || {
    echo 'Output must not exist' >&2; exit 2
}
mkdir "$1"
cd "$1"
work=$(pwd -P)
# Recheck resolved paths. They become GCC specs and linker arguments.
case "$work:$sysroot" in
    *[!a-zA-Z0-9_./:+-]*) echo 'Resolved paths contain unsupported characters' >&2; exit 2 ;;
esac
"$CC" --version > gcc.version
"$CC" -dumpfullversion > gcc.release
"$CC" -dumpmachine > gcc.target
"$LLD" --version > lld.version
"$READELF" --version > readelf.version
version=$(cat gcc.release)
target=$(cat gcc.target)
case "$version" in 16.*) ;; *) echo 'GCC16 is required' >&2; exit 2 ;; esac
case "$target" in aarch64*-netbsd*) ;; *) echo 'AArch64 NetBSD ABI is required' >&2; exit 2 ;; esac
grep -Eq '^LLD 23\.' lld.version
runtime=$sysroot/usr/pkg/gcc16/lib
crt=$runtime/gcc/$target/$version
for input in "$crt/crtbegin.o" "$crt/crtbeginS.o" "$crt/libgcc.a" \
    "$runtime/libgcc_s.so" "$sysroot/usr/lib/crti.o" \
    "$sysroot/lib/libc.so" "$sysroot/libexec/ld.elf_so"; do
    [ -f "$input" ] || { echo "Missing target input: $input" >&2; exit 2; }
done
"$CC" -dumpspecs > original.specs
"$CC" -print-prog-name=as > assembler.path
"$CC" -print-prog-name=ld > default-linker.path
assembler=$(cat assembler.path)
default_linker=$(cat default-linker.path)
case "$assembler:$default_linker" in
    *[!a-zA-Z0-9_./:+-]*) echo 'Unsupported configured tool path' >&2; exit 2 ;;
esac
case "$assembler" in /*) ;; *) echo 'Configured assembler is not absolute' >&2; exit 2 ;; esac
case "$default_linker" in /*) ;; *) echo 'Configured linker is not absolute' >&2; exit 2 ;; esac
"$assembler" --version > assembler.version
"$default_linker" --version > default-linker.version
grep -q 'GNU assembler' assembler.version
grep -q 'GNU ld' default-linker.version
cksum "$CC" "${CXX:-$CC}" "$assembler" "$default_linker" > original-tools.cksum
# An absolute configured --with-ld can override -B and -fuse-ld selection.
# This changes only this invocation. Direct ELF linking does not test LTO.
# Preserve a control with the original loader and the selected LLD/common aliases.
# Then repair only the three known loader rules in invocation-local specs.
# LLD accepts -d for compatibility; final links allocate COMMON without it.
# Relocatable (-r) equivalence is deliberately outside this test.
awk -v linker="$LLD" '
    /^\*/ { block=$0 }
    block == "*linker:" && $0 != block && NF {
        if ($0 != "collect2") exit 1
        print linker; selected++; next
    }
    block == "*link:" || block == "*netbsd_link_spec:" {
        dc += gsub(/ -dc /, " -d ")
        dp += gsub(/ -dp /, " -d ")
    }
    { print }
    END { if (dc != 2 || dp != 2 || selected != 1) exit 1 }
' original.specs > original-loader.specs
awk '
    /^\*/ { block=$0 }
    block == "*link:" || block == "*netbsd_link_spec:" ||
        block == "*netbsd_link_ld_elf_so:" {
        replaced[block] += gsub(/-dynamic-linker \/usr\/libexec\/ld[.]elf_so}/,
            "-dynamic-linker /libexec/ld.elf_so}")
    }
    /\/usr\/libexec\/ld[.]elf_so/ { unexpected++ }
    { print }
    END {
        if (replaced["*link:"] != 1 || replaced["*netbsd_link_spec:"] != 1 ||
            replaced["*netbsd_link_ld_elf_so:"] != 1 || unexpected) {
            print "Unsupported GCC loader specs: require one rule in each known block" > "/dev/stderr"
            exit 1
        }
    }
' original-loader.specs > selected-linker.specs
run_cc()
{
    "$CC" --sysroot="$sysroot" -B"$crt/" -B"$sysroot/usr/lib/" \
        -L"$runtime" -specs="$work/selected-linker.specs" "$@"
}
run_link()
{
    # LLD23 does not accept GCC's aarch64nbsd emulation name. Keep all
    # other GCC target specs and startup objects. Select the real target loader.
    run_cc -fno-use-linker-plugin "$@" -Wl,-m,aarch64elf -Wl,-rpath-link,"$sysroot/lib" \
        -Wl,-rpath-link,"$sysroot/usr/lib" -Wl,-z,relro -Wl,-z,now
}
[ "$(run_cc -print-file-name=crtbegin.o)" = "$crt/crtbegin.o" ]
[ "$(run_cc -print-libgcc-file-name)" = "$crt/libgcc.a" ]
cat > answer.c <<'C'
int ember_lld_answer(void);

int
ember_lld_answer(void)
{
	return 42;
}
C
cat > main.c <<'C'
#include <stdio.h>

extern int ember_lld_answer(void);

int
main(void)
{
	int value;

	value = ember_lld_answer();
	if (printf("%d\n", value) < 0)
		return 2;
	return value != 42;
}
C
cat > unresolved.c <<'C'
extern int ember_lld_missing(void);
int ember_lld_unresolved(void);

int
ember_lld_unresolved(void)
{
	return ember_lld_missing();
}
C
cat > common-a.c <<'C'
int ember_lld_common;
C
cat > common-b.c <<'C'
int ember_lld_common;
C
run_cc -v -fno-lto -std=c23 -Wall -Wextra -Werror -fPIC -c answer.c -o answer.o \
    > compile.log 2>&1
awk -v tool="$assembler" 'index($0, " " tool " ") == 1 { print; found=1 }
    END { if (!found) exit 1 }' compile.log > assembler-invocation.txt
run_cc -fno-lto -std=c23 -Wall -Wextra -Werror -fPIE -c main.c -o main.o > main-compile.log 2>&1
run_link -v -Wl,-v -shared -Wl,--no-undefined,--fatal-warnings \
    -Wl,-soname,libember-gcc16-lld.so.1 answer.o -o libember-gcc16-lld.so.1 \
    > shared-link.log 2>&1
grep -F "$LLD " shared-link.log > linker-invocation.txt
grep -F "$(cat lld.version)" shared-link.log > linker-banner.txt
ln -s libember-gcc16-lld.so.1 libember-gcc16-lld.so
run_link -v -Wl,-v -pie -Wl,--no-undefined,--fatal-warnings \
    main.o -L"$work" -lember-gcc16-lld \
    '-Wl,-rpath,$ORIGIN:/usr/pkg/gcc16/lib' -o consumer > executable-link.log 2>&1
grep -F "$LLD " executable-link.log > executable-linker-invocation.txt
grep -F "$(cat lld.version)" executable-link.log > executable-linker-banner.txt
# The control uses the same objects, linker and strict flags. Only its specs
# retain the original loader. A successful link alone must not accept that ELF.
"$CC" --sysroot="$sysroot" -B"$crt/" -B"$sysroot/usr/lib/" -L"$runtime" \
    -specs="$work/original-loader.specs" -fno-use-linker-plugin -v -Wl,-v \
    -Wl,-m,aarch64elf -Wl,-rpath-link,"$sysroot/lib" \
    -Wl,-rpath-link,"$sysroot/usr/lib" -Wl,-z,relro -Wl,-z,now \
    -pie -Wl,--no-undefined,--fatal-warnings main.o -L"$work" -lember-gcc16-lld \
    '-Wl,-rpath,$ORIGIN:/usr/pkg/gcc16/lib' -o consumer-original-loader \
    > original-loader-link.log 2>&1
"$READELF" -lW consumer-original-loader > consumer-original-loader.segments
grep -F '[Requesting program interpreter: /usr/libexec/ld.elf_so]' \
    consumer-original-loader.segments
if grep -F '[Requesting program interpreter: /libexec/ld.elf_so]' \
    consumer-original-loader.segments; then
    echo 'Original loader control unexpectedly met the target interpreter contract' >&2
    exit 1
fi
printf '%s\n' 'PASS: original loader specs still link but fail the target interpreter contract'
for artifact in libember-gcc16-lld.so.1 consumer; do
    "$READELF" -h "$artifact" > "$artifact.header"
    "$READELF" -lW "$artifact" > "$artifact.segments"
    "$READELF" -n "$artifact" > "$artifact.notes"
    "$READELF" -dW "$artifact" > "$artifact.dynamic"
    grep -Eq 'Class:[[:space:]]+ELF64' "$artifact.header"
    grep -Eq 'Machine:[[:space:]]+AArch64' "$artifact.header"
    grep -Eq 'Type:[[:space:]]+DYN' "$artifact.header"
    grep -q '\.note.netbsd.ident' "$artifact.notes"
    grep -Eq 'IDENT 1100000000 \(11\.0\.0\)' "$artifact.notes"
    grep -q '\.note.netbsd.pax' "$artifact.notes"
    grep -q 'PaX' "$artifact.notes"
    grep -q 'GNU_RELRO' "$artifact.segments"
    grep -Eq 'BIND_NOW|FLAGS.*NOW' "$artifact.dynamic"
    if grep -F "$sysroot" "$artifact.dynamic"; then
        echo 'Sysroot leaked into dynamic metadata' >&2; exit 1
    fi
done
grep -F '[Requesting program interpreter: /libexec/ld.elf_so]' consumer.segments
if grep -q 'INTERP' libember-gcc16-lld.so.1.segments; then
    echo 'Shared library contains an interpreter' >&2; exit 1
fi
grep -F '[libember-gcc16-lld.so.1]' consumer.dynamic
grep -F '[libember-gcc16-lld.so.1]' libember-gcc16-lld.so.1.dynamic
printf '%s\n' 'PASS: GCC16 invoked its GNU assembler and selected LLD23 through specs' \
    'PASS: AArch64 DSO/PIE retain EmberBSD interpreter, NetBSD11/PaX notes and RELRO/NOW'

run_cc -fno-lto -std=c23 -Wall -Wextra -Werror -fPIC -c unresolved.c -o unresolved.o \
    > unresolved-compile.log 2>&1
if run_link -shared -Wl,--no-undefined,--fatal-warnings unresolved.o \
    -o unresolved.so > unresolved-link.log 2>&1; then
    echo 'Undefined symbol unexpectedly linked' >&2; exit 1
fi
grep -Eq 'error: undefined symbol: ember_lld_missing' unresolved-link.log
printf '%s\n' 'PASS: real undefined symbol is rejected'

for name in common-a common-b; do
    run_cc -fno-lto -std=c23 -Wall -Wextra -Werror -fPIC -fcommon -c "$name.c" \
        -o "$name.o" > "$name-compile.log" 2>&1
    "$READELF" -sW "$name.o" > "$name.symbols"
    grep -Eq 'COM[[:space:]]+ember_lld_common$' "$name.symbols"
done
# The first link must succeed and emit a warning. The second changes only
# the output name and --fatal-warnings. An unrelated link error cannot pass.
run_link -shared -Wl,--no-undefined,--warn-common common-a.o common-b.o \
    -o common-warning.so > common-warning.log 2>&1
grep -Eq 'warning: multiple common of ember_lld_common' common-warning.log
"$READELF" -sW common-warning.so > common-warning.symbols
awk '$8 == "ember_lld_common" && $7 ~ /^[0-9]+$/ { found=1 }
    END { if (!found) exit 1 }' common-warning.symbols
if run_link -shared -Wl,--no-undefined,--warn-common,--fatal-warnings \
    common-a.o common-b.o -o common-fatal.so > common-fatal.log 2>&1; then
    echo 'Fatal linker warning unexpectedly succeeded' >&2; exit 1
fi
grep -Eq 'error: multiple common of ember_lld_common' common-fatal.log
printf '%s\n' 'PASS: common-symbol warning succeeds normally and fails with --fatal-warnings'
cksum consumer libember-gcc16-lld.so.1 > artifacts.cksum
if [ -n "${CXX:-}" ]; then
    "$CXX" --version > cxx.version
    [ "$("$CXX" -dumpfullversion)" = "$version" ]
    [ "$("$CXX" -dumpmachine)" = "$target" ]
    cxx_headers=$sysroot/usr/pkg/gcc16/include/c++
    [ -f "$cxx_headers/stdexcept" ]
    [ -f "$cxx_headers/$target/bits/c++config.h" ]
    run_cxx()
    {
        "$CXX" --sysroot="$sysroot" -B"$crt/" -B"$sysroot/usr/lib/" \
            -L"$runtime" -specs="$work/selected-linker.specs" -nostdinc++ \
            -isystem "$cxx_headers" -isystem "$cxx_headers/$target" "$@"
    }
    cat > exception.cc <<'CXX'
#include <stdexcept>

extern "C" void ember_lld_throw();
void ember_lld_throw() { throw std::runtime_error("ember-lld"); }
CXX
    cat > catch.cc <<'CXX'
#include <cstdio>
#include <cstring>
#include <stdexcept>

extern "C" void ember_lld_throw();
int main()
{
    try {
        ember_lld_throw();
    } catch (const std::runtime_error &error) {
        if (std::strcmp(error.what(), "ember-lld") != 0)
            return 2;
        return std::puts("C++ DSO exception PASS") < 0 ? 3 : 0;
    }
    return 1;
}
CXX
    run_cxx -fno-lto -std=c++20 -Wall -Wextra -Werror -fPIC -c exception.cc \
        -o exception.o > exception-compile.log 2>&1
    run_cxx -fno-lto -std=c++20 -Wall -Wextra -Werror -fPIE -c catch.cc \
        -o catch.o > catch-compile.log 2>&1
    run_cxx -fno-use-linker-plugin -v -Wl,-v -Wl,-m,aarch64elf -shared \
        -Wl,--no-undefined,--fatal-warnings -Wl,-z,relro,-z,now \
        -Wl,-soname,libember-gcc16-lld-cxx.so.1 \
        -Wl,-rpath,/usr/pkg/gcc16/lib exception.o \
        -o libember-gcc16-lld-cxx.so.1 > exception-link.log 2>&1
    ln -s libember-gcc16-lld-cxx.so.1 libember-gcc16-lld-cxx.so
    run_cxx -fno-use-linker-plugin -v -Wl,-v -Wl,-m,aarch64elf -pie \
        -Wl,--no-undefined,--fatal-warnings -Wl,-z,relro,-z,now \
        catch.o -L"$work" -lember-gcc16-lld-cxx \
        '-Wl,-rpath,$ORIGIN:/usr/pkg/gcc16/lib' -o consumer-cxx > catch-link.log 2>&1
    for log in exception-link.log catch-link.log; do
        grep -F "$LLD " "$log" > "$log.invocation"
        grep -F "$(cat lld.version)" "$log" > "$log.banner"
    done
    for artifact in consumer-cxx libember-gcc16-lld-cxx.so.1; do
        "$READELF" -h "$artifact" > "$artifact.header"
        "$READELF" -lW "$artifact" > "$artifact.segments"
        "$READELF" -dW "$artifact" > "$artifact.dynamic"
        "$READELF" -n "$artifact" > "$artifact.notes"
        grep -Eq 'Class:[[:space:]]+ELF64' "$artifact.header"
        grep -Eq 'Machine:[[:space:]]+AArch64' "$artifact.header"
        grep -Eq 'Type:[[:space:]]+DYN' "$artifact.header"
        grep -Eq 'IDENT 1100000000 \(11\.0\.0\)' "$artifact.notes"
        grep -q 'PaX' "$artifact.notes"
        grep -q 'GNU_RELRO' "$artifact.segments"
        grep -Eq 'BIND_NOW|FLAGS.*NOW' "$artifact.dynamic"
        grep -F '[libstdc++.so.7]' "$artifact.dynamic"
        grep -F '[libgcc_s.so.1]' "$artifact.dynamic"
        if grep -F "$sysroot" "$artifact.dynamic"; then exit 1; fi
    done
    grep -F '[Requesting program interpreter: /libexec/ld.elf_so]' consumer-cxx.segments
    if grep -q 'INTERP' libember-gcc16-lld-cxx.so.1.segments; then
        echo 'C++ shared library contains an interpreter' >&2; exit 1
    fi
    cksum consumer-cxx libember-gcc16-lld-cxx.so.1 >> artifacts.cksum
    echo 'PASS: optional C++ exception DSO and consumer link with the common GCC16 runtime'
else
    echo 'SKIP: optional C++ link check (set CXX to the matching GCC16 driver)'
fi
for object in ./*.o; do
    "$READELF" -SW "$object" > "$object.sections"
    if grep -q '\.gnu.lto' "$object.sections"; then
        echo 'Unexpected GCC LTO object' >&2; exit 1
    fi
done
cksum "$CC" "${CXX:-$CC}" "$assembler" "$default_linker" > final-tools.cksum
cmp original-tools.cksum final-tools.cksum
printf '%s\n' 'PASS: compiler and configured GNU assembler/linker remain unchanged; objects contain no GCC LTO sections' \
    'NOT RUN: target execution, LTO, or compiler default migration'
