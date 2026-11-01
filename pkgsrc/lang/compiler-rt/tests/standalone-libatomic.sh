#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# On NetBSD architectures that need it, compiler-rt supplies one shared
# clang_rt.atomic lock table. RV32 instead uses the libc provider.
# Usage: standalone-libatomic.sh CC SYSROOT PREFIX_LIB READELF NM NEW_WORK
set -eu
[ "$#" = 6 ] || { echo 'usage: standalone-libatomic.sh CC SYSROOT PREFIX_LIB READELF NM NEW_WORK' >&2; exit 2; }
cc=$1 sysroot=$2 lib=$3 readelf=$4 nm=$5 work=$6
for p in "$cc" "$sysroot" "$lib" "$readelf" "$nm" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
here=$(cd "$(dirname "$0")/.." && pwd)
mk=$here/Makefile
[ ! -e "$here/../../local-robotics/gcc16-libatomic" ] || { echo 'FAIL: a second (GCC 16) libatomic package exists'; exit 1; }
mkdir "$work"
cat > "$work/t.c" <<'EOS'
#include <stdint.h>
typedef struct { void *a, *b; } P;
typedef struct { char c[32]; } B;
_Alignas(8) volatile uint64_t a8;
_Alignas(8) P p16;
_Alignas(32) B p32;
int main(void) {
	uint64_t x;
	P p = { 0, &p16 }, e;
	B b = {{ 0 }}, c;
	(void)__atomic_fetch_add(&a8, 1, __ATOMIC_SEQ_CST);
	__atomic_load(&p16, &e, __ATOMIC_ACQUIRE);
	(void)__atomic_compare_exchange(&p16, &e, &p, 0,
	    __ATOMIC_SEQ_CST, __ATOMIC_ACQUIRE);
	__atomic_store(&p16, &p, __ATOMIC_SEQ_CST);
	__atomic_load(&p32, &c, __ATOMIC_ACQUIRE);
	__atomic_store(&p32, &b, __ATOMIC_SEQ_CST);
	__atomic_load(&a8, &x, __ATOMIC_SEQ_CST);
	return (int)x + c.c[0];
}
EOS
target=$($cc -dumpmachine)
case "$target" in
	riscv32*-netbsd)
		grep -q '^CMAKE_CONFIGURE_ARGS+=.*-DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=ON' "$mk" ||
			{ echo 'FAIL: RV32 compiler-rt overlaps the libc atomic provider'; exit 1; }
		grep -q '^CMAKE_CONFIGURE_ARGS+=.*-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=OFF' "$mk" ||
			{ echo 'FAIL: RV32 compiler-rt builds a second atomic provider'; exit 1; }
		grep -q 'libatomic-libc.ldscript' "$mk" ||
			{ echo 'FAIL: RV32 recipe does not preserve the -latomic linker interface'; exit 1; }
		for f in "$lib/libatomic.so" "$lib/libatomic.a"; do
			[ -f "$f" ] || { echo "FAIL: missing libc-backed linker script $f"; exit 1; }
			grep -qx 'INPUT(-lc)' "$f" || { echo "FAIL: unexpected linker script $f"; exit 1; }
		done
		"$cc" --sysroot="$sysroot" -x c -std=c11 -O2 "$work/t.c" -o "$work/t"
		if "$nm" -u "$work/t" | grep -q '__atomic_'; then
			echo 'FAIL: RV32 libc did not resolve generic atomics'; exit 1
		fi
		"$cc" --sysroot="$sysroot" -x c -std=c11 -O2 "$work/t.c" -L"$lib" -latomic -o "$work/with-atomic"
		if "$nm" -u "$work/with-atomic" | grep -q '__atomic_'; then
			echo 'FAIL: RV32 -latomic linker script did not resolve libc atomics'; exit 1
		fi
		"$cc" --sysroot="$sysroot" -static -x c -std=c11 -O2 "$work/t.c" -L"$lib" -latomic -o "$work/static-with-atomic"
		if "$nm" -u "$work/static-with-atomic" | grep -q '__atomic_'; then
			echo 'FAIL: RV32 static -latomic linker script did not resolve libc atomics'; exit 1
		fi
		echo 'PASS: RV32 generic atomics link through libc with and without -latomic'
		exit 0
		;;
esac
cat > "$work/t.cpp" <<'EOS'
#include <atomic>
#include <cstdint>
struct P { void *a, *b; };
struct B { char c[32]; };
std::atomic<uint64_t> a8;
std::atomic<P> a16;
std::atomic<B> a32;
int main() {
	a8.fetch_add(1);
	P p{nullptr, &p}, e = a16.load();
	a16.compare_exchange_strong(e, p);
	B b{}, c = a32.load();
	a32.store(b);
	return (int)a8.load() + c.c[0];
}
EOS
grep -q '^CMAKE_CONFIGURE_ARGS+=.*-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=ON' "$mk" ||
	{ echo 'FAIL: recipe does not build the standalone libatomic'; exit 1; }
grep -q 'lib/libatomic.so$' "$mk" || { echo 'FAIL: recipe does not install -latomic'; exit 1; }
if "$cc" --sysroot="$sysroot" -O2 "$work/t.cpp" -o "$work/no-atomic" 2> "$work/no-atomic.log"; then
	echo 'FAIL: generic atomics linked without libatomic; the probe tests nothing'; exit 1
fi
grep -q '__atomic_' "$work/no-atomic.log"
"$cc" --sysroot="$sysroot" -O2 "$work/t.cpp" -L"$lib" -latomic -o "$work/t"
real=$(cd "$lib" && ls libclang_rt.atomic-*.so)
needed=$("$readelf" -d "$work/t" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')
printf '%s\n' "$needed" | grep -qx "$real" || { echo "FAIL: probe does not need $real"; exit 1; }
if printf '%s\n' "$needed" | grep -E 'libatomic|libgcc'; then echo 'FAIL: GCC runtime linked'; exit 1; fi
defs=$("$nm" -D --defined-only "$lib/$real")
for s in __atomic_load __atomic_store __atomic_compare_exchange __atomic_exchange; do
	printf '%s\n' "$defs" | grep -q " $s\$" || { echo "FAIL: $s missing"; exit 1; }
done
echo "PASS: generic atomics link to $real through -latomic"
