#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). libc++ must use the NetBSD C locale when a
# program selects _XOPEN_SOURCE or _POSIX_C_SOURCE, which hide LC_C_LOCALE.
# Usage: libcxx-netbsd-c-locale.sh CXX TARGET SYSROOT LIBCXX_INCLUDE [PATCH]
# With PATCH, a copy of LIBCXX_INCLUDE (libcxx/include of the runtime source,
# or an installed c++/v1) is patched with -p1 first.
set -eu
[ $# -ge 4 ] && [ $# -le 5 ] || { echo 'usage: libcxx-netbsd-c-locale.sh CXX TARGET SYSROOT LIBCXX_INCLUDE [PATCH]' >&2; exit 2; }
cxx=$1 target=$2 sysroot=$3 include=$4 patch=${5:-}
work=$(mktemp -d "${TMPDIR:-/tmp}/libcxx-c-locale.XXXXXX")
trap 'rm -rf "$work"' EXIT
if [ -n "$patch" ]; then
    mkdir -p "$work/libcxx"
    cp -R "$include" "$work/libcxx/include"
    (cd "$work" && ${PATCH_TOOL:-patch} -s -p1 --forward < "$patch")
    include=$work/libcxx/include
fi
cat > "$work/probe.cc" <<'EOC'
#include <iomanip>
#include <locale>
#include <sstream>
int main() {
    std::ostringstream out;
    out << std::put_money(12345.0L);
    std::time_get<char> const &get = std::use_facet<std::time_get<char> >(std::locale::classic());
    (void)get;
    return out.str() == "12345" ? 0 : 1;
}
EOC
# The default namespace (_NETBSD_SOURCE) also declares the libc object.
for define in -D_XOPEN_SOURCE=700 -D_POSIX_C_SOURCE=200809L -D_NETBSD_SOURCE; do
    "$cxx" --target="$target" --sysroot="$sysroot" -fuse-ld=lld -std=c++17 \
        -nostdinc++ -isystem "$include" "$define" "$work/probe.cc" -o "$work/probe" \
        -L"$sysroot/usr/pkg/llvm/lib" -lc++ 2> "$work/err" || {
        sed -n 1,20p "$work/err" >&2
        echo "FAIL: libc++ C locale with $define" >&2; exit 1; }
done
echo 'PASS: libc++ uses the NetBSD C locale under strict feature macros'
