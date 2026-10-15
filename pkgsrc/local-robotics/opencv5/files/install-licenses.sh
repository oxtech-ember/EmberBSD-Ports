#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
mkdir -p "$prefix/share/licenses/opencv5" "$prefix/share/doc/opencv5"
cp "$source/LICENSE" "$prefix/share/licenses/opencv5/LICENSE"
cp "$recipe/files/SOURCE" "$prefix/share/doc/opencv5/SOURCE"
# Preserve notices for the selected upstream implementation sources.
find "$source/3rdparty" -type f \( -iname '*license*' -o -iname '*copying*' \) | LC_ALL=C sort | while IFS= read -r file; do
    relative=${file#"$source/"}
    mkdir -p "$prefix/share/licenses/opencv5/$(dirname "$relative")"
    cp "$file" "$prefix/share/licenses/opencv5/$relative"
done
