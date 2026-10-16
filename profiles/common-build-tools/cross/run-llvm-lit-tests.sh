#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed upstream lit package acceptance.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 UPSTREAM_LIT_TESTS NEW_OUTPUT" >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] || exit 2
tests=$1 work=$2
for path do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2;; esac
done
export PATH=/usr/pkg/gcc16/bin:/usr/pkg/bin:/usr/pkg/sbin:/bin:/usr/bin:/sbin:/usr/sbin
unset PYTHONHOME PYTHONPATH LD_LIBRARY_PATH LD_PRELOAD
mkdir "$work"
pkg_info -e py315-llvm-lit-23.1.3nb1
pkg_admin check py315-llvm-lit > "$work/package-integrity.txt"
metadata=/usr/pkg/lib/python3.15/site-packages/lit-23.1.3.dev0.dist-info
grep -Fx 'Version: 23.1.3.dev0' "$metadata/METADATA"
grep -Fx 'Root-Is-Purelib: true' "$metadata/WHEEL"
grep -Fx 'Tag: py3-none-any' "$metadata/WHEEL"
test -s "$metadata/licenses/LICENSE.TXT"
for command in lit llvm-lit; do
    head -1 "/usr/pkg/bin/$command" | grep -Fx '#!/usr/pkg/bin/python3.15'
    "$command" --version | tee "$work/$command-version.txt"
    grep -q '23.1.3dev' "$work/$command-version.txt"
done
mkdir "$work/suite"
# Use the upstream configuration unchanged; no local Python implementation.
cp "$tests/Inputs/shtest-shell/lit.cfg" "$work/suite/lit.cfg"
printf '# RUN: true\n' > "$work/suite/pass.txt"
printf '# RUN: false\n' > "$work/suite/fail.txt"
printf '# XFAIL: *\n# RUN: false\n' > "$work/suite/expected.txt"
cd "$work"
llvm-lit -v suite/pass.txt suite/expected.txt > pass.txt 2>&1
grep -q 'PASS:' pass.txt
grep -q 'XFAIL:' pass.txt
if llvm-lit -v suite/fail.txt > fail.txt 2>&1; then
    echo 'Failed test incorrectly returned success.' >&2; exit 1
else
    test "$?" = 1
fi
grep -q 'FAIL:' fail.txt
echo 'PASS: installed wheel metadata, launcher, module, passing/expected/failed shell tests.'
