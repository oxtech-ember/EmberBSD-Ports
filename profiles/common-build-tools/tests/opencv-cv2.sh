#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). There is one cv2, built with every module.
# Usage: opencv-cv2.sh [PYTHON SITEDIR]
# Without arguments, check the recipes: only graphics/opencv-contrib, which
# builds the OpenCV and contrib modules together, installs cv2, and
# graphics/opencv does not build it. With PYTHON and a SITEDIR that holds
# the built cv2, check that cv2 has the contrib APIs its users need,
# such as CascadeClassifier (xobjdetect in OpenCV 5) for py-Willow.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
g=$here/../../../pkgsrc/graphics
fail=0
grep -q '^\${PYSITELIB}/cv2/' "$g/opencv/PLIST" &&
    { echo "FAIL: graphics/opencv installs cv2"; fail=1; }
grep -q '^\${PYSITELIB}/cv2/python-\${PYVERSSUFFIX}/cv2.so$' "$g/opencv-contrib/PLIST" ||
    { echo "FAIL: graphics/opencv-contrib does not install cv2"; fail=1; }
grep -q 'DBUILD_opencv_python3=OFF' "$g/opencv/Makefile" ||
    { echo "FAIL: graphics/opencv builds cv2"; fail=1; }
grep -q 'DBUILD_opencv_python3=ON' "$g/opencv-contrib/Makefile" ||
    { echo "FAIL: graphics/opencv-contrib does not build cv2"; fail=1; }
grep -q 'graphics/opencv/options.mk' "$g/opencv-contrib/Makefile" ||
    { echo "FAIL: graphics/opencv-contrib does not use the options of graphics/opencv"; fail=1; }
for m in face ml plot tracking xobjdetect; do
    grep -q "^INSTALL_DIRS.*modules/$m" "$g/opencv-contrib/Makefile" ||
        { echo "FAIL: graphics/opencv-contrib does not install $m"; fail=1; }
done
if [ "$#" = 2 ]; then
    PYTHONPATH=$2 "$1" - <<'PY' || fail=1
import cv2
missing = [a for a in ("CascadeClassifier", "face", "ml", "plot", "legacy")
           if not hasattr(cv2, a)]
if missing:
    raise SystemExit("FAIL: cv2 %s lacks %s" % (cv2.__version__, ", ".join(missing)))
import numpy
c = cv2.CascadeClassifier()
assert c.empty()
r = cv2.face.LBPHFaceRecognizer_create()
r.train([numpy.zeros((8, 8), numpy.uint8)], numpy.array([1]))
print("cv2", cv2.__version__, "ok")
PY
elif [ "$#" != 0 ]; then
    echo "Usage: $0 [PYTHON SITEDIR]" >&2; exit 2
fi
[ "$fail" = 0 ] && echo "PASS: one cv2 in graphics/opencv-contrib"
exit "$fail"
