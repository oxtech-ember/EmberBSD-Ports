#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Split within DESTDIR; never edit the live prefix.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
case "$prefix" in /|/usr/pkg|/usr/local) echo "A private staging prefix is required." >&2; exit 2;; esac
[ -f "$prefix/lib/libboost_iostreams.so.1.92.0" ]
[ -d "$prefix/lib/cmake/boost_iostreams-1.92.0-shared" ]
[ -f "$prefix/lib/libboost_random.so.1.92.0" ]
[ -d "$prefix/lib/cmake/boost_random-1.92.0-shared" ]
rm -rf "$prefix/include" "$prefix/share/boost-1.92.0"
for directory in "$prefix/lib/cmake/"*; do
    case "${directory##*/}" in boost_iostreams-1.92.0-shared|boost_random-1.92.0-shared|boost_dynamic_bitset-1.92.0) ;; *) rm -rf "$directory";; esac
done
for library in "$prefix/lib/"*; do
    [ -d "$library" ] && continue
    case "${library##*/}" in libboost_iostreams.so*|libboost_random.so*) ;; *) rm -f "$library";; esac
done
mkdir -p "$prefix/share/licenses/boost-iostreams"
cp "$source/LICENSE_1_0.txt" "$prefix/share/licenses/boost-iostreams/LICENSE"
cp "$recipe/files/SOURCE" "$prefix/share/licenses/boost-iostreams/SOURCE"
