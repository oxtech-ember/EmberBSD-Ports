#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual installed package lifecycle and planning.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
mkdir -p "$out/first" "$out/reinstalled" "$out/upstream"
export PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin
LC_ALL=C; export LC_ALL
for package in eigen3 boost-headers boost-libs ompl; do
    if pkg_info -e "$package" > /dev/null 2>&1; then
        echo "Preserve the existing installed package: $package" >&2; exit 2
    fi
done
install_packages()
{
    pkg_add "$packages/eigen3-5.0.1.tgz"
    pkg_add "$packages/boost-headers-1.92.0.tgz"
    pkg_add "$packages/boost-libs-1.92.0.tgz"
    pkg_add "$packages/ompl-2.0.2.tgz"
}
install_packages > "$out/install.log" 2>&1
for package in eigen3 boost-headers boost-libs ompl; do
    pkg_admin check "$package" > "$out/$package-integrity.log" 2>&1
    pkg_info -B "$package" > "$out/$package-build-info.txt"
done
ldd "$tests/ompl-contract" > "$out/contract-linkage.txt"
ldd "$tests/ember-ompl-path" > "$out/example-linkage.txt"
ldd "$tests/ompl-dependency-contract" > "$out/dependency-linkage.txt"
grep -F /usr/pkg/lib/libboost_program_options.so.1.92.0 "$out/dependency-linkage.txt" > /dev/null
for linkage in "$out/contract-linkage.txt" "$out/example-linkage.txt"; do
    for library in /usr/pkg/lib/libompl.so.19 /usr/pkg/lib/libboost_serialization.so.1.92.0 \
        /usr/pkg/gcc16/lib/libstdc++.so.7 /usr/pkg/gcc16/lib/libgcc_s.so.1; do
        grep -F "$library" "$linkage" > /dev/null
    done
    if grep -E 'not found|/workspace/|libstdc\+\+\.so\.9|libpython|libvamp' "$linkage"; then exit 1; fi
done
"$tests/geometry-contract" > "$out/geometry.log" 2>&1
"$tests/test-path-geometry" > "$out/example-geometry.log" 2>&1
"$tests/ompl-dependency-contract" > "$out/dependencies.log" 2>&1
"$tests/ompl-pkgconfig-contract" > "$out/pkgconfig-archive.log" 2>&1
for mode in path invalid-goal blocked; do
    "$tests/ompl-contract" "$mode" > "$out/first/$mode.log" 2>&1
done
"$tests/ember-ompl-path" --output "$out/first/path.csv" > "$out/first/stdout.txt" 2> "$out/first/example.log"
[ ! -s "$out/first/stdout.txt" ]
"$tests/ember-ompl-path" --output - > "$out/first/stdout.csv" 2> "$out/first/example-stdout.log"
cmp "$out/first/path.csv" "$out/first/stdout.csv"
expect()
{
    expected=$1 name=$2; shift 2
    status=0
    "$tests/ember-ompl-path" "$@" > "$out/$name.stdout" 2> "$out/$name.log" || status=$?
    echo "$status" > "$out/$name.status"
    [ "$status" = "$expected" ]
}
expect 3 invalid-goal --case invalid-goal --output "$out/negative.csv"
expect 3 blocked --case blocked --output "$out/negative.csv"
[ ! -e "$out/negative.csv" ]
expect 2 invalid-option --unknown
expect 2 missing-value --output
expect 4 missing-output --output "$out/missing-directory/path.csv"
if [ -e /dev/full ]; then
    expect 4 full-output --output /dev/full
else
    echo 'SKIP: /dev/full is absent' > "$out/full-output.skip"
fi
# Run selected bounded, unmodified upstream tests. Long planner benchmarks
# and optional feature suites are outside this acceptance profile.
for name in test_adjacency_list test_heap test_grid test_gridb test_pdf \
    test_random test_halton_sampling test_state_operations test_state_spaces \
    test_state_storage test_planner_data test_ptc test_fmt_null_goal; do
    status=0
    (cd "$out/upstream" && "$tests/upstream/$name") > "$out/upstream/$name.log" 2>&1 || status=$?
    echo "$status" > "$out/upstream/$name.status"
    [ "$status" = 0 ] || { cat "$out/upstream/$name.log" >&2; exit 1; }
    echo "PASS: $name"
done
status=0
pkg_delete boost-libs > "$out/dependency-delete.log" 2>&1 || status=$?
[ "$status" -ne 0 ]
pkg_info -e boost-libs > /dev/null
for package in ompl boost-libs boost-headers eigen3; do
    pkg_delete "$package" >> "$out/remove.log" 2>&1
    if pkg_info -e "$package" > /dev/null 2>&1; then exit 1; fi
done
[ ! -e /usr/pkg/lib/libompl.so ]
install_packages > "$out/reinstall.log" 2>&1
"$tests/ompl-contract" path > "$out/reinstalled/path.log" 2>&1
"$tests/ember-ompl-path" --output "$out/reinstalled/path.csv" > "$out/reinstalled/stdout.txt" 2> "$out/reinstalled/example.log"
cmp "$out/first/path.csv" "$out/reinstalled/path.csv"
for package in eigen3 boost-headers boost-libs ompl; do
    pkg_admin check "$package" > "$out/$package-reinstalled-integrity.log" 2>&1
done
pkg_info -a > "$out/packages.txt"
echo 'PASS: installed path planning, independent geometry, error controls and package lifecycle'
