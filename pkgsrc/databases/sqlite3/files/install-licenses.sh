#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Keep original public-domain and build-tool notices.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
license=$prefix/share/licenses/sqlite3
mkdir -p "$license"
cp "$recipe/files/SOURCE" "$license/"
cp "$source/autosetup/LICENSE" "$license/autosetup-LICENSE"
# The public-domain dedication is an original part of sqlite3.h. The complete
# header is also installed at include/sqlite3.h, with its embedded notices.
sed -n '1,25p' "$source/sqlite3.h" > "$license/SQLite-public-domain.txt"
