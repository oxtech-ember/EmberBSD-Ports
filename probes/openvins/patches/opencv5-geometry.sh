#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). OpenCV 5.0 moved findFundamentalMat
# and undistortPoints (including cv::fisheye) from calib3d to the
# geometry module; add the needed include to every caller.
set -eu
cd "$1"
grep -rl -e 'findFundamentalMat' -e 'undistortPoints' ov_core/src ov_msckf/src |
while read fname; do
    grep -q geometry/3d "$fname" && continue
    sed -i '1i\
#include <opencv2/geometry/3d.hpp>' "$fname"
done
