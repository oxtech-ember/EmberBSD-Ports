#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
mkdir -p "$prefix/share/licenses/rtabmap" "$prefix/share/doc/rtabmap"
cp "$source/LICENSE" "$prefix/share/licenses/rtabmap/BSD.txt"
cp "$recipe/licenses/"*.txt "$prefix/share/licenses/rtabmap/"
cp "$recipe/files/SOURCE" "$prefix/share/doc/rtabmap/SOURCE"
cp "$source/utilite/include/rtabmap/utilite/UThread.h" "$prefix/share/licenses/rtabmap/utilite-LGPL-notice.h"
cp "$source/corelib/src/rtflann/general.h" "$prefix/share/licenses/rtabmap/rtflann-BSD-notice.h"
cp "$source/corelib/src/rtflann/ext/lz4.c" "$prefix/share/licenses/rtabmap/rtflann-lz4-BSD-notice.c"
cp "$source/corelib/include/rtabmap/core/rvl_codec.h" "$prefix/share/licenses/rtabmap/RVL-MIT-notice.h"
