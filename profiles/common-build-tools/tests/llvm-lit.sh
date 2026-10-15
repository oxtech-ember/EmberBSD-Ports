#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, upstream lit module/launcher source independence contract.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 LLVM_ARCHIVE NEW_WORK" >&2; exit 2; }
archive=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
python=${PYTHON:-python3.15}
command -v "$python" >/dev/null 2>&1 || { echo 'Python315 is required for the common lit source check' >&2; exit 2; }
version=$("$python" --version)
case "$version" in 'Python 3.15.'*) ;; *) echo "Python315 is required: $version" >&2; exit 2 ;; esac
printf '%s\n' "$version"
mkdir "$work/source"
tar -xf "$archive" -C "$work/source" llvm-project-23.1.3.src/llvm/utils/lit
source=$work/source/llvm-project-23.1.3.src/llvm/utils/lit
"$python" -m venv "$work/venv"
# Stage the actual upstream module for the named import/launcher contract.
# This is not a wheel build/install or PLIST acceptance.
site=$(find "$work/venv/lib" -type d -name site-packages)
[ -n "$site" ] && [ "$(printf '%s\n' "$site" | wc -l | tr -d ' ')" = 1 ]
cp -R "$source/lit" "$site/"
cp "$source/lit.py" "$work/venv/bin/llvm-lit"
mkdir "$work/suite"
cp "$source/tests/Inputs/shtest-shell/lit.cfg" "$work/suite/lit.cfg"
printf '# RUN: true\n' > "$work/suite/pass.txt"
printf '# RUN: false\n' > "$work/suite/fail.txt"
printf '# XFAIL: *\n# RUN: false\n' > "$work/suite/expected.txt"
mv "$work/source" "$work/source-unavailable"
unset PYTHONPATH
"$work/venv/bin/python" "$work/venv/bin/llvm-lit" --version | tee "$work/version.log"
grep -q '23.1.3dev' "$work/version.log"
"$work/venv/bin/python" "$work/venv/bin/llvm-lit" -v "$work/suite/pass.txt" "$work/suite/expected.txt" > "$work/pass.log" 2>&1
grep -q 'PASS:' "$work/pass.log"
grep -q 'XFAIL:' "$work/pass.log"
set +e
"$work/venv/bin/python" "$work/venv/bin/llvm-lit" -v "$work/suite/fail.txt" > "$work/fail.log" 2>&1
status=$?
set -e
[ "$status" = 1 ] || { echo "FAIL: actual lit failure status $status" >&2; exit 1; }
grep -q 'FAIL:' "$work/fail.log"
echo 'PASS: upstream lit on Python315, source-independent launcher and actual PASS/XFAIL/FAIL=>1'
echo 'PENDING: wheel metadata/entry shebang/package PLIST/native common Python'
