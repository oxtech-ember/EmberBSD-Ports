#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
fail() { echo "$*" >&2; exit 2; }
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || fail 'Usage: build.sh ABS_NEW_WORK [ABS_CACHE]'
work=$1
for path in "$@"; do
    case "$path" in /*) ;; *) fail 'Use absolute paths.' ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) fail 'Use simple paths.' ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || fail 'Work path already exists.'
case "$(uname -s):$(uname -m)" in
    NetBSD:aarch64) ;;
    Darwin:arm64) [ "${HOST_CHECK:-0}" = 1 ] || fail 'Darwin requires HOST_CHECK=1.' ;;
    *) fail 'Use NetBSD/aarch64 or an explicit Darwin/arm64 host check.' ;;
esac
positive() {
    case "$2" in ''|*[!0-9]*) fail "$1 must be a positive integer." ;; esac
    [ "$2" -gt 0 ] 2>/dev/null || fail "$1 must be positive."
}
jobs=${JOBS:-1}
positive JOBS "$jobs"
if [ "${BUILD_AS_KIB+x}" = x ]; then positive BUILD_AS_KIB "$BUILD_AS_KIB"; ulimit -S -v "$BUILD_AS_KIB"; fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
cmake=${CMAKE:-cmake}
for tool in "$cmake" ninja tar patch; do command -v "$tool" >/dev/null; done
sha() {
    if command -v sha256 >/dev/null; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
while read -r name expected url; do
    if [ "$#" = 2 ]; then cp "$2/$name" "$work/archives/$name";
    else curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"; fi
    [ "$(sha "$work/archives/$name")" = "$expected" ] || fail "Source checksum mismatch: $name"
    printf '%s %s %s\n' "$name" "$expected" "$url" >> "$work/logs/sources.txt"
    tar -mxf "$work/archives/$name" -C "$work/src"
done < "$recipe/sources.tsv"
while read -r name expected; do
    [ "$(sha "$recipe/$name")" = "$expected" ] || fail "Patch checksum mismatch: $name"
    patch -f -F0 -p0 -d "$work/src/libxml2-2.15.4" < "$recipe/$name" > "$work/logs/schema-patch.log" 2>&1
done < "$recipe/patches.tsv"
support=$recipe/../../profiles/common-media/recipes/textproc/libxml2/files
while read -r expected name; do
    [ "$(sha "$support/$name")" = "$expected" ] || fail "Test driver checksum mismatch: $name"
    cp "$support/$name" "$work/src/libxml2-2.15.4/$name"
done < "$support/test-support.sha256"
export CC=${CC:-/usr/bin/cc}
{ uname -a; "$CC" --version; "$cmake" --version; ninja --version;
  printf 'JOBS=%s\nBUILD_AS_KIB=%s\n' "$jobs" "${BUILD_AS_KIB:-inherited}";
} > "$work/logs/tools.txt"
run() {
    stage=$1; shift
    result=0
    "$@" > "$work/logs/$stage.log" 2>&1 || result=$?
    if [ "$result" -ne 0 ]; then tail -60 "$work/logs/$stage.log" >&2; exit "$result"; fi
}
prefix=$work/install
run configure "$cmake" -S "$work/src/libxml2-2.15.4" -B "$work/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_INSTALL_RPATH="$prefix/lib" -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
    -DBUILD_SHARED_LIBS=ON -DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_DOCS=OFF \
    -DLIBXML2_WITH_TESTS=ON -DLIBXML2_WITH_PROGRAMS=ON -DLIBXML2_WITH_ICONV=ON \
    -DLIBXML2_WITH_ICU=OFF -DLIBXML2_WITH_HTTP=OFF -DLIBXML2_WITH_LEGACY=OFF \
    -DLIBXML2_WITH_ZLIB=OFF -DLIBXML2_WITH_THREADS=ON -DLIBXML2_WITH_VALID=ON \
    -DLIBXML2_WITH_XPATH=ON -DLIBXML2_WITH_READER=ON -DLIBXML2_WITH_WRITER=ON \
    -DLIBXML2_WITH_HTML=ON -DLIBXML2_WITH_SCHEMAS=ON -DLIBXML2_WITH_RELAXNG=ON \
    -DLIBXML2_WITH_OUTPUT=ON -DLIBXML2_WITH_XINCLUDE=ON -DLIBXML2_WITH_C14N=ON
run build "$cmake" --build "$work/build" --parallel "$jobs"
run install "$cmake" --install "$work/build"
mkdir -p "$prefix/share/ember-libxml2/licenses"
cp "$recipe/sources.tsv" "$recipe/patches.tsv" "$recipe/PROVENANCE.md" "$prefix/share/ember-libxml2/"
cp "$work/src/libxml2-2.15.4/Copyright" "$prefix/share/ember-libxml2/licenses/Copyright"
for source in dict.c list.c; do
    sed -n '1,/^ \*\//p' "$work/src/libxml2-2.15.4/$source" > "$prefix/share/ember-libxml2/licenses/$source-notice.txt"
done
echo "Installed libxml2 2.15.4 provider in $prefix; run test.sh next."
