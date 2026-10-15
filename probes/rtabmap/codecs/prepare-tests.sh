#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Copy actual upstream tests and fixtures.
set -eu
[ "$#" = 3 ] || { echo 'Usage: prepare-tests.sh WORK PREFIX NEW_TESTS' >&2; exit 2; }
work=$1 prefix=$2 out=$3
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
mkdir -p "$out/bin" "$out/fixtures" "$out/licenses"
for name in pngtest pngvalid; do cp "$work/png/build/.libs/$name" "$out/bin/$name"; done
cp "$work/jpeg/build/tjunittest" "$out/bin/tjunittest"
for name in cjpeg djpeg; do cp "$work/jpeg/stage$prefix/bin/$name" "$out/bin/$name"; done
cp "$work/png/source/pngtest.png" "$out/fixtures/"
cp "$work/jpeg/source/testimages/testorig.ppm" "$work/jpeg/source/testimages/testorig.jpg" "$out/fixtures/"
cp "$work/png/source/LICENSE" "$out/licenses/png-LICENSE"
cp "$work/jpeg/source/LICENSE.md" "$out/licenses/jpeg-LICENSE.md"
cp "$work/jpeg/source/testimages/LICENSE.txt" "$out/licenses/jpeg-testimages-LICENSE.txt"
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
cp "$recipe/run-tests.sh" "$recipe/sources.tsv" "$out/"
chmod +x "$out/bin/"* "$out/run-tests.sh"
(cd "$out" && find bin fixtures licenses -type f -exec sha256sum {} \;) > "$out/inputs.sha256"
