#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Link the libattr version script the way a non-Linux build does: only the
# attr_* API is defined, because the *xattr functions come from libc there.
# ld.lld rejects version script entries for symbols that are not defined.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 EXPORTS CLANG NEW_WORK" >&2; exit 2; }
exports=$1 cc=$2
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
sed -n 's/^[[:space:]]*\(attr_[a-z_]*\);$/\1/p' "$exports" > "$work/api"
test -s "$work/api"
while read -r name; do printf 'void %s(void) {}\n' "$name"; done \
    < "$work/api" > "$work/stub.c"
"$cc" --target=aarch64--netbsd -fPIC -shared -nostdlib -fuse-ld=lld \
    -Wl,--version-script,"$exports" -o "$work/libattr.so" "$work/stub.c"
llvm_readelf=${LLVM_READELF:-$(dirname "$cc")/llvm-readelf}
"$llvm_readelf" --dyn-syms "$work/libattr.so" > "$work/dynsym"
while read -r name; do
    grep -q " $name@@ATTR_1\.[0-9]*\$" "$work/dynsym" ||
        { echo "FAIL: $name is not exported with a version" >&2; exit 1; }
done < "$work/api"
if grep -q 'xattr' "$work/dynsym"; then
    echo "FAIL: libattr exports an xattr symbol" >&2; exit 1
fi
echo "PASS: the version script links with only the attr_* API defined"
