#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). OpenCV 5.0.0 dnn with the external protobuf.
# Usage: opencv-dnn-protobuf.sh [WRKSRC]
# OpenCV 5.0.0 removed opencv-caffe.proto but its caffe_io still includes the
# old generated opencv-caffe.pb.h, so the recipe (PROTOBUF_UPDATE_FILES=ON)
# fails in modules/dnn. Without arguments, check that graphics/opencv carries
# the upstream f7ad23157f backport. With the patched WRKSRC of
# graphics/opencv or graphics/opencv-contrib, check that no dnn source still
# needs the Caffe leftovers and that the replacement helpers are present.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
g=$here/../../../pkgsrc/graphics/opencv
fail=0
patch=patch-modules_dnn_protobuf__io
if [ -f "$g/patches/$patch" ]; then
    # distinfo holds the SHA1 of the patch without its $NetBSD$ lines.
    sum=$(sed '/\$NetBSD.*/d' "$g/patches/$patch" | openssl sha1 | sed 's/.* //')
    grep -qx "SHA1 ($patch) = $sum" "$g/distinfo" ||
        { echo "FAIL: distinfo does not hold the SHA1 of $patch"; fail=1; }
else
    echo "FAIL: graphics/opencv lacks $patch"; fail=1
fi
grep -q '^[^#]*RM.*modules/dnn/src/caffe.*modules/dnn/misc/caffe' "$g/Makefile.common" ||
    { echo "FAIL: Makefile.common does not remove the Caffe leftovers"; fail=1; }
grep -q '^PATCHDIR=.*graphics/opencv/patches' "$g/../opencv-contrib/Makefile" ||
    { echo "FAIL: graphics/opencv-contrib does not use the opencv patches"; fail=1; }
if [ "$#" = 1 ]; then
    dnn=$1/modules/dnn
    [ -d "$dnn" ] || { echo "Usage: $0 [WRKSRC]" >&2; exit 2; }
    for d in src/caffe misc/caffe; do
        [ ! -e "$dnn/$d" ] || { echo "FAIL: $d is still in $dnn"; fail=1; }
    done
    for f in src/protobuf_io.cpp src/protobuf_io.hpp src/glog_emulator.hpp; do
        [ -f "$dnn/$f" ] || { echo "FAIL: $dnn/$f is missing"; fail=1; }
    done
    # Skip the *.orig copies that the patch step leaves.
    if find "$dnn/src" "$dnn/CMakeLists.txt" -type f ! -name '*.orig' -exec \
        grep -lE 'opencv-caffe\.pb\.h|caffe/caffe_io\.hpp|caffe/glog_emulator\.hpp|misc/caffe' {} + |
        grep .; then
        echo "FAIL: dnn sources still need the Caffe leftovers"; fail=1
    fi
elif [ "$#" != 0 ]; then
    echo "Usage: $0 [WRKSRC]" >&2; exit 2
fi
[ "$fail" = 0 ] && echo "PASS: OpenCV dnn builds its protobuf readers without Caffe leftovers"
exit "$fail"
