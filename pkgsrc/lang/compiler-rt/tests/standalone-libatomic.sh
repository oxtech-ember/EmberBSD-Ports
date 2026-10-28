#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# compiler-rt is the only libatomic: a shared clang_rt.atomic reached as
# -latomic. Generic (locked) atomics do not link with the builtins alone
# and link to that one library, not to GCC's libatomic.
# Usage: standalone-libatomic.sh CXX SYSROOT PREFIX_LIB READELF NM NEW_WORK
set -eu
[ "$#" = 6 ] || { echo 'usage: standalone-libatomic.sh CXX SYSROOT PREFIX_LIB READELF NM NEW_WORK' >&2; exit 2; }
cxx=$1 sysroot=$2 lib=$3 readelf=$4 nm=$5 work=$6
for p in "$cxx" "$sysroot" "$lib" "$readelf" "$nm" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
here=$(cd "$(dirname "$0")/.." && pwd)
mk=$here/Makefile
grep -q '^CMAKE_CONFIGURE_ARGS+=.*-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=ON' "$mk" ||
	{ echo 'FAIL: recipe does not build the standalone libatomic'; exit 1; }
grep -q 'lib/libatomic.so$' "$mk" || { echo 'FAIL: recipe does not install -latomic'; exit 1; }
[ ! -e "$here/../../local-robotics/gcc16-libatomic" ] || { echo 'FAIL: a second (GCC 16) libatomic package exists'; exit 1; }
mkdir "$work"
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
if "$cxx" --sysroot="$sysroot" -O2 "$work/t.cpp" -o "$work/no-atomic" 2> "$work/no-atomic.log"; then
	echo 'FAIL: generic atomics linked without libatomic; the probe tests nothing'; exit 1
fi
grep -q '__atomic_' "$work/no-atomic.log"
"$cxx" --sysroot="$sysroot" -O2 "$work/t.cpp" -L"$lib" -latomic -o "$work/t"
real=$(cd "$lib" && ls libclang_rt.atomic-*.so)
needed=$("$readelf" -d "$work/t" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')
printf '%s\n' "$needed" | grep -qx "$real" || { echo "FAIL: probe does not need $real"; exit 1; }
if printf '%s\n' "$needed" | grep -E 'libatomic|libgcc'; then echo 'FAIL: GCC runtime linked'; exit 1; fi
defs=$("$nm" -D --defined-only "$lib/$real")
for s in __atomic_load __atomic_store __atomic_compare_exchange __atomic_exchange; do
	printf '%s\n' "$defs" | grep -q " $s\$" || { echo "FAIL: $s missing"; exit 1; }
done
echo "PASS: generic atomics link to $real through -latomic"
