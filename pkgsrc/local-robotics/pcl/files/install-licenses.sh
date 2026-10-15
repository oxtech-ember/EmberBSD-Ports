#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Preserve PCL and embedded source licenses.
set -eu
[ "$#" = 3 ] || exit 2
source=$1 prefix=$2 recipe=$3
licenses=$prefix/share/licenses/pcl
mkdir -p "$licenses"
cp "$source/LICENSE.txt" "$licenses/"
cp "$recipe/files/SOURCE" "$licenses/"
cp "$source/common/src/fft/kiss_fft.c" "$licenses/KissFFT-kiss_fft.c"
cp "$source/io/src/lzf.cpp" "$licenses/LZF-lzf.cpp"
cp "$source/io/include/pcl/io/ply/ply.h" "$licenses/PLY-ply.h"
