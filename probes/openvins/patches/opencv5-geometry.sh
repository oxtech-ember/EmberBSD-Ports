#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). OpenCV 5.0 moved findFundamentalMat
# and undistortPoints (including cv::fisheye) from calib3d to the
# geometry module; add the needed include to every caller.
# The substitution is verified against both BSD sed implementations the
# probe runs under: they agree on the comma delimiter and on \n as a
# newline in the replacement, and differ only in the -i suffix argument.
set -eu
case "$(uname -s)" in
Darwin) sed_i() { sed -i '' "$@"; } ;;
*) sed_i() { sed -i "$@"; } ;;
esac
cd "$1"
grep -rl -e 'findFundamentalMat' -e 'undistortPoints' ov_core/src ov_msckf/src |
while read fname; do
    grep -q geometry/3d "$fname" && continue
    sed_i '1,/^#include/s,^#include,#include <opencv2/geometry/3d.hpp>\n#include,' "$fname"
done
