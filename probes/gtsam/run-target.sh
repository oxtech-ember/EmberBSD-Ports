#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Actual installed-package graph acceptance.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
for name in gtsam eigen3; do
    if pkg_info -e "$name" > /dev/null 2>&1; then
        echo "Preserve installed package: $name" >&2; exit 2
    fi
done
mkdir -p "$out/first" "$out/reinstalled" "$out/upstream" "$out/controls"
install_packages()
{
    pkg_add "$packages/eigen3-5.0.1.tgz"
    pkg_add "$packages/gtsam-4.3.0.tgz"
}
install_packages > "$out/install.log" 2>&1
echo 'PASS: packages installed'
for name in eigen3 gtsam; do
    pkg_admin check "$name" > "$out/$name-integrity.log" 2>&1
    pkg_info -B "$name" > "$out/$name-build-info.txt"
done
for binary in gtsam-contract ember-gtsam-graph; do
    ldd "$tests/$binary" > "$out/$binary-linkage.txt"
    for library in /usr/pkg/lib/libgtsam.so.4 /usr/pkg/gcc16/lib/libstdc++.so.7 /usr/pkg/gcc16/lib/libgcc_s.so.1; do
        grep -F "$library" "$out/$binary-linkage.txt" > /dev/null
    done
    if grep -E 'not found|/workspace/|libstdc\+\+\.so\.9|libtbb|libboost|libpython|libmetis' "$out/$binary-linkage.txt"; then exit 1; fi
done
"$tests/gtsam-matrix-check" > "$out/matrix-check.log" 2>&1
for mode in linear-fusion pose-graph underconstrained missing-state; do
    "$tests/gtsam-contract" "$mode" > "$out/first/$mode.log" 2>&1
done
for mode in linear pose; do
    "$tests/ember-gtsam-graph" --case "$mode" --output "$out/first/$mode.csv" > "$out/first/$mode.stdout" 2> "$out/first/$mode-example.log"
    [ ! -s "$out/first/$mode.stdout" ]
    "$tests/check-gtsam-csv" "$mode" "$out/first/$mode.csv" > "$out/first/$mode-check.log" 2>&1
    "$tests/ember-gtsam-graph" --case "$mode" --output - > "$out/first/$mode-stdout.csv" 2> "$out/first/$mode-stdout.log"
    cmp "$out/first/$mode.csv" "$out/first/$mode-stdout.csv"
done
echo 'PASS: known linear and nonlinear solutions, covariance and CSV'
for bad in 10 nan inf -inf; do
    sed "s/^linear,optimized,0,[^,]*/linear,optimized,0,$bad/" "$out/first/linear.csv" > "$out/controls/wrong-$bad.csv"
    status=0
    "$tests/check-gtsam-csv" linear "$out/controls/wrong-$bad.csv" > "$out/controls/wrong-$bad.log" 2>&1 || status=$?
    [ "$status" = 1 ]
done
expect()
{
    expected=$1 name=$2; shift 2
    status=0
    "$tests/ember-gtsam-graph" "$@" > "$out/controls/$name.stdout" 2> "$out/controls/$name.log" || status=$?
    echo "$status" > "$out/controls/$name.status"
    [ "$status" = "$expected" ]
}
for mode in underconstrained missing-state; do
    expect 65 "$mode" --case "$mode" --output "$out/controls/negative.csv"
    [ ! -e "$out/controls/negative.csv" ]
    printf 'preserve\n' > "$out/controls/preserved.csv"
    expect 65 "$mode-preserve" --case "$mode" --output "$out/controls/preserved.csv"
    [ "$(cat "$out/controls/preserved.csv")" = preserve ]
done
expect 64 invalid-option --unknown
expect 64 missing-value --output
expect 74 missing-directory --case linear --output "$out/missing/graph.csv"
expect 74 output-directory --case linear --output "$out/controls"
[ -e /dev/full ]
expect 74 full-output --case linear --output /dev/full
status=0
"$tests/ember-gtsam-graph" --case linear --output - > /dev/full 2> "$out/controls/full-stdout.log" || status=$?
echo "$status" > "$out/controls/full-stdout.status"
[ "$status" = 74 ]
for name in testPose2 testOrdering testGaussianFactorGraph testJacobianFactor \
    testLinearExceptions testValues testPriorFactor testBetweenFactor \
    testNonlinearOptimizer testNonlinearFactorGraph testMarginals; do
    status=0
    (cd "$out/upstream" && "$tests/upstream/$name") > "$out/upstream/$name.log" 2>&1 || status=$?
    echo "$status" > "$out/upstream/$name.status"
    [ "$status" = 0 ] || { cat "$out/upstream/$name.log" >&2; exit 1; }
    echo "PASS: $name"
done
status=0
pkg_delete eigen3 > "$out/dependency-delete.log" 2>&1 || status=$?
[ "$status" -ne 0 ]
pkg_info -e eigen3 > /dev/null
for package in gtsam eigen3; do
    pkg_delete "$package" >> "$out/remove.log" 2>&1
    if pkg_info -e "$package" > /dev/null 2>&1; then exit 1; fi
done
for library in /usr/pkg/lib/libgtsam.so /usr/pkg/lib/libcephes-gtsam.so; do
    [ ! -e "$library" ] && [ ! -L "$library" ]
done
install_packages > "$out/reinstall.log" 2>&1
for mode in linear pose; do
    "$tests/ember-gtsam-graph" --case "$mode" --output "$out/reinstalled/$mode.csv" > "$out/reinstalled/$mode.stdout" 2> "$out/reinstalled/$mode.log"
    "$tests/check-gtsam-csv" "$mode" "$out/reinstalled/$mode.csv" > "$out/reinstalled/$mode-check.log" 2>&1
    cmp "$out/first/$mode.csv" "$out/reinstalled/$mode.csv"
done
for package in eigen3 gtsam; do
    pkg_admin check "$package" > "$out/$package-reinstalled-integrity.log" 2>&1
done
pkg_info -a > "$out/packages.txt"
echo 'PASS: installed graph optimization, error contracts and package lifecycle'
