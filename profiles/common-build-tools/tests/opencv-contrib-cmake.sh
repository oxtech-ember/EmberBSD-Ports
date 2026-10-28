#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). OpenCV contrib modules are CMake components.
# Usage: opencv-contrib-cmake.sh OPENCV_PREFIX WORKDIR
# OPENCV_PREFIX has graphics/opencv's lib/cmake/opencv5 (from the patched
# OpenCVConfig.cmake.in) and the libraries of both OpenCV packages.
# A consumer asks for the xobjdetect, ml and face components: without
# opencv-contrib's OpenCVContribModules.cmake it must fail to configure,
# with it it must build and run.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 OPENCV_PREFIX WORKDIR" >&2; exit 2; }
prefix=$1 work=$2
here=$(cd "$(dirname "$0")" && pwd)
fragment=$here/../../../pkgsrc/graphics/opencv-contrib/files/OpenCVContribModules.cmake
cmake=${CMAKE:-cmake}
rm -rf "$work"; mkdir -p "$work/src" "$work/stage/lib/cmake"
ln -s "$prefix/include" "$work/stage/include"
for f in "$prefix"/lib/libopencv_*; do ln -s "$f" "$work/stage/lib/"; done
cp -R "$prefix/lib/cmake/opencv5" "$work/stage/lib/cmake/"
rm -f "$work/stage/lib/cmake/opencv5/OpenCVContribModules.cmake"
cat > "$work/src/CMakeLists.txt" <<'CM'
cmake_minimum_required(VERSION 3.16)
project(cvc CXX)
find_package(OpenCV 5.0 REQUIRED COMPONENTS core imgproc ml xobjdetect face)
add_executable(cvc cvc.cpp)
target_link_libraries(cvc ${OpenCV_LIBS})
CM
cat > "$work/src/cvc.cpp" <<'CPP'
#include <opencv2/core.hpp>
#include <opencv2/ml.hpp>
#include <opencv2/xobjdetect.hpp>
#include <opencv2/face.hpp>
int main() {
    cv::CascadeClassifier cc;
    cv::Ptr<cv::ml::KNearest> kn = cv::ml::KNearest::create();
    cv::Ptr<cv::face::LBPHFaceRecognizer> fr = cv::face::LBPHFaceRecognizer::create();
    return cc.empty() && !kn.empty() && !fr.empty() ? 0 : 1;
}
CPP
if "$cmake" -S "$work/src" -B "$work/without" -DOpenCV_DIR="$work/stage/lib/cmake/opencv5" > "$work/without.log" 2>&1; then
    echo "FAIL: contrib components found without OpenCVContribModules.cmake" >&2; exit 1
fi
grep -q xobjdetect "$work/without.log" ||
    { echo "FAIL: configure without the fragment failed for another reason" >&2; cat "$work/without.log" >&2; exit 1; }
cp "$fragment" "$work/stage/lib/cmake/opencv5/"
"$cmake" -S "$work/src" -B "$work/with" -DOpenCV_DIR="$work/stage/lib/cmake/opencv5" > "$work/with.log" 2>&1 ||
    { echo "FAIL: configure with OpenCVContribModules.cmake" >&2; cat "$work/with.log" >&2; exit 1; }
"$cmake" --build "$work/with" > "$work/build.log" 2>&1 ||
    { echo "FAIL: build" >&2; cat "$work/build.log" >&2; exit 1; }
"$work/with/cvc" || { echo "FAIL: run" >&2; exit 1; }
echo 'PASS: OpenCV contrib modules are find_package components.'
