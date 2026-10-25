#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
. "$recipe/common.sh"
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || fail 'Usage: build.sh ABS_NEW_WORK [ABS_CACHE]'
work=$1
for path in "$@"; do absolute "$path"; done
[ ! -e "$work" ] && [ ! -L "$work" ] || fail 'Work path already exists.'
[ -n "${XML_PREFIX:-}" ] || fail 'Set XML_PREFIX to the common libxml2 2.15.4 provider.'
absolute "$XML_PREFIX"
[ -f "$XML_PREFIX/share/ember-libxml2/sources.tsv" ] || fail 'XML_PREFIX is not a completed project libxml2 provider.'
cmp "$recipe/../libxml2/sources.tsv" "$XML_PREFIX/share/ember-libxml2/sources.tsv" >/dev/null || fail 'XML provider source inventory differs.'
case "$(uname -s):$(uname -m)" in
    NetBSD:aarch64) platform=netbsd; dep_prefix=${DEPENDENCY_PREFIX:-/usr/pkg} ;;
    Darwin:arm64) [ "${HOST_CHECK:-0}" = 1 ] || fail 'Darwin requires HOST_CHECK=1.'
        platform=darwin; dep_prefix=${DEPENDENCY_PREFIX:-/opt/homebrew} ;;
    *) fail 'Use NetBSD/aarch64 or an explicit Darwin/arm64 host check.' ;;
esac
jobs=${JOBS:-1}
positive JOBS "$jobs"
if [ "${BUILD_AS_KIB+x}" = x ]; then positive BUILD_AS_KIB "$BUILD_AS_KIB"; ulimit -S -v "$BUILD_AS_KIB"; fi
cmake=${CMAKE:-cmake}
for tool in "$cmake" ninja tar patch; do command -v "$tool" >/dev/null; done
verify_recipe
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
while read -r name expected url; do
    if [ "$#" = 2 ]; then cp "$2/$name" "$work/archives/$name";
    else curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"; fi
    [ "$(sha "$work/archives/$name")" = "$expected" ] || fail "Source checksum mismatch: $name"
    printf '%s %s %s\n' "$name" "$expected" "$url" >> "$work/logs/sources.txt"
    case "$name" in *.tar.gz) tar -mxf "$work/archives/$name" -C "$work/src" ;; esac
done < "$recipe/sources.tsv"
while read -r name expected url; do
    if [ "$#" = 2 ]; then cp "$2/$name" "$work/archives/$name";
    else curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"; fi
done < "$recipe/../../pkgsrc/devel/libiio/files/sources.tsv"
: "${PY:?Select the absolute Python interpreter}"
: "${PATCH:?Select the absolute patch executable}"
"$PY" "$recipe/../../profiles/sdr-receivers/cross/prepare-libiio.py" "$work/archives" "$work/src/libiio-1.0.0"
while read -r source file before after; do
    [ "$(sha "$work/src/$source/$file")" = "$before" ] || fail "Unexpected upstream source: $source/$file"
done < "$recipe/patched-files.tsv"
while read -r source name expected; do
    patch -d "$work/src/$source" -p0 < "$recipe/$name" >> "$work/logs/patches.log"
done < "$recipe/patches.tsv"
while read -r source file before after; do
    [ "$(sha "$work/src/$source/$file")" = "$after" ] || fail "Unexpected patched source: $source/$file"
done < "$recipe/patched-files.tsv"
prefix=$work/install
mkdir -p "$prefix/include/iio-compat-0"
cp "$work/src/libiio-1.0.0/.ember/iio.h" "$prefix/include/iio-compat-0/iio.h"
export CC=${CC:-/usr/bin/cc} CXX=${CXX:-/usr/bin/c++}
{ uname -a; "$CC" --version; "$CXX" --version; "$cmake" --version; ninja --version;
  printf 'JOBS=%s\nBUILD_AS_KIB=%s\n' "$jobs" "${BUILD_AS_KIB:-inherited}";
} > "$work/logs/tools.txt"
xml_inc=$XML_PREFIX/include/libxml2
if [ "$platform" = darwin ]; then
    xml_lib=$XML_PREFIX/lib/libxml2.dylib
    zstd_lib=${LIBZSTD_LIBRARIES:-$dep_prefix/lib/libzstd.dylib}
else
    xml_lib=$XML_PREFIX/lib/libxml2.so
    zstd_lib=${LIBZSTD_LIBRARIES:-$dep_prefix/lib/libzstd.so}
fi
zstd_inc=${LIBZSTD_INCLUDE_DIR:-$dep_prefix/include}
[ -f "$xml_inc/libxml/parser.h" ] && [ -f "$xml_lib" ] || fail 'Provide installed libxml2 paths.'
[ -f "$zstd_inc/zstd.h" ] && [ -f "$zstd_lib" ] || fail 'Provide installed Zstandard paths.'
run libiio-configure "$cmake" -S "$work/src/libiio-1.0.0" -B "$work/libiio" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;$XML_PREFIX/lib;$dep_prefix/lib" -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
    -C "$recipe/../../pkgsrc/devel/libiio/files/receiver.cmake" \
    -DLIBXML2_INCLUDE_DIR="$xml_inc" -DLIBXML2_LIBRARY="$xml_lib" \
    -DLIBZSTD_INCLUDE_DIR="$zstd_inc" -DLIBZSTD_LIBRARIES="$zstd_lib"
run libiio-build "$cmake" --build "$work/libiio" --parallel "$jobs"
run libiio-install "$cmake" --install "$work/libiio"
run soapy-configure "$cmake" -S "$work/src/SoapySDR-soapy-sdr-0.8.1" -B "$work/soapy" -G Ninja \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_RPATH="$prefix/lib" -DENABLE_PYTHON=OFF \
    -DENABLE_PYTHON3=OFF -DENABLE_TESTS=OFF -DENABLE_DOCS=OFF
run soapy-build "$cmake" --build "$work/soapy" --parallel "$jobs"
run soapy-install "$cmake" --install "$work/soapy"
run ad9361-configure "$cmake" -S "$work/src/libad9361-iio-0.3" -B "$work/ad9361" -G Ninja \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib" -DLIBIIO_INCLUDEDIR="$prefix/include/iio-compat-0" \
    -DLIBIIO_LIBRARIES="$prefix/lib/libiio.so.0" -DPYTHON_BINDINGS=OFF -DMATLAB_BINDINGS=OFF \
    -DWITH_DOC=OFF -DOSX_PACKAGE=OFF -DENABLE_PACKAGING=OFF
run ad9361-build "$cmake" --build "$work/ad9361" --target ad9361 --parallel "$jobs"
run ad9361-install "$cmake" --install "$work/ad9361"
if [ "$platform" = darwin ]; then
    ad_include=$prefix/lib/ad9361.framework/Headers
    ad_library=$prefix/lib/ad9361.framework/ad9361
else
    ad_include=$prefix/include
    ad_library=$prefix/lib/libad9361.so
fi
run pluto-configure "$cmake" -S "$work/src/SoapyPlutoSDR-soapy-plutosdr-0.2.2" -B "$work/pluto" -G Ninja \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_PREFIX_PATH="$prefix" -DCMAKE_INSTALL_RPATH="$prefix/lib" \
    -DLibIIO_INCLUDE_DIR="$prefix/include/iio-compat-0" -DLibIIO_LIBRARY="$prefix/lib/libiio.so.0" \
    -DLibAD9361_INCLUDE_DIR="$ad_include" -DLibAD9361_LIBRARY="$ad_library" \
    -DCMAKE_DISABLE_FIND_PACKAGE_LibUSB=ON
run pluto-build "$cmake" --build "$work/pluto" --parallel "$jobs"
run pluto-install "$cmake" --install "$work/pluto"
mkdir -p "$prefix/share/ember-sdr/licenses"
printf '%s\n' "$XML_PREFIX" > "$prefix/share/ember-sdr/xml-prefix"
cp "$XML_PREFIX/share/ember-libxml2/sources.tsv" "$prefix/share/ember-sdr/xml-sources.tsv"
cp "$recipe/sources.tsv" "$recipe/patches.tsv" "$recipe/PROVENANCE.md" "$prefix/share/ember-sdr/"
cp "$recipe/../../pkgsrc/devel/libiio/files/sources.tsv" "$prefix/share/ember-sdr/libiio-sources.tsv"
cp "$recipe/../../pkgsrc/devel/libiio/distinfo" "$prefix/share/ember-sdr/libiio-distinfo"
cp "$work/src/libiio-1.0.0/COPYING.txt" "$prefix/share/ember-sdr/licenses/libiio-LGPL-2.1"
cp "$work/src/libiio-1.0.0/COPYING_MIT.txt" "$prefix/share/ember-sdr/licenses/libiio-MIT"
cp "$work/src/libiio-1.0.0/COPYING_GPL.txt" "$prefix/share/ember-sdr/licenses/libiio-GPL"
cp "$work/src/SoapySDR-soapy-sdr-0.8.1/LICENSE_1_0.txt" "$prefix/share/ember-sdr/licenses/SoapySDR-BSL-1.0"
cp "$work/src/SoapyPlutoSDR-soapy-plutosdr-0.2.2/LICENSE" "$prefix/share/ember-sdr/licenses/SoapyPluto-LGPL-2.1"
cp "$work/src/libad9361-iio-0.3/LICENSE" "$prefix/share/ember-sdr/licenses/libad9361-LGPL-2.1"
echo "Installed in $prefix; run test.sh next. Hardware RX remains unverified."
