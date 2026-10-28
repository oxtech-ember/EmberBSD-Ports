#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Real installed PCL and dependency acceptance.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
all='eigen3 boost-headers boost-libs compiler-rt lz4 flann-lib pcl'
for name in $all; do
    if pkg_info -e "$name" > /dev/null 2>&1; then echo "Preserve installed package: $name" >&2; exit 2; fi
done
mkdir -p "$out/first" "$out/reinstalled" "$out/upstream" "$out/controls"
install_packages()
{
    for package in eigen3-5.0.1 boost-headers-1.92.0 boost-libs-1.92.0 compiler-rt-23.1.4nb9 lz4-1.10.0 flann-lib-1.9.2 pcl-1.15.1nb1; do
        pkg_add "$packages/$package.tgz"
    done
}
install_packages > "$out/install.log" 2>&1
for name in $all; do
    pkg_admin check "$name" > "$out/$name-integrity.log" 2>&1
    pkg_info -B "$name" > "$out/$name-build-info.txt"
done
echo 'PASS: all seven actual packages installed and checked'
for binary in pcl-contract pcl-expanded-contract ember-pcl-cloud atomic-contract boost-iostreams-contract; do
    ldd "$tests/$binary" > "$out/$binary-linkage.txt"
    grep -F /usr/pkg/gcc16/lib/libstdc++.so.7 "$out/$binary-linkage.txt" > /dev/null
    grep -F /usr/pkg/gcc16/lib/libgcc_s.so.1 "$out/$binary-linkage.txt" > /dev/null
    if grep -E 'not found|/workspace/|libstdc\+\+\.so\.9|libgomp|libvtk|libQt|libpython' "$out/$binary-linkage.txt"; then exit 1; fi
done
for library in /usr/pkg/lib/libpcl_common.so.1.15 /usr/pkg/lib/libpcl_filters.so.1.15 /usr/pkg/lib/libpcl_registration.so.1.15 /usr/pkg/lib/liblz4.so.1; do
    grep -F "$library" "$out/pcl-contract-linkage.txt" > /dev/null
done
for library in libpcl_surface.so.1.15 libpcl_segmentation.so.1.15; do
    grep -F "/usr/pkg/lib/$library" "$out/pcl-expanded-contract-linkage.txt" > /dev/null
done
grep -F /usr/pkg/gcc16/lib/libatomic.so.3 "$out/atomic-contract-linkage.txt" > /dev/null
grep -F /usr/pkg/lib/libboost_iostreams.so.1.92.0 "$out/boost-iostreams-contract-linkage.txt" > /dev/null
grep -F /usr/pkg/lib/libboost_random.so.1.92.0 "$out/boost-iostreams-contract-linkage.txt" > /dev/null
for binary in pcl-matrix-check lz4-zero-buffers boost-iostreams-contract atomic-contract; do
    "$tests/$binary" > "$out/$binary.log" 2>&1
done
printf 'PCL dependency CLI roundtrip\n' > "$out/lz4-input.txt"
lz4 -f "$out/lz4-input.txt" "$out/lz4-input.lz4" > "$out/lz4-compress.log" 2>&1
lz4 -d -f "$out/lz4-input.lz4" "$out/lz4-decoded.txt" > "$out/lz4-decompress.log" 2>&1
cmp "$out/lz4-input.txt" "$out/lz4-decoded.txt"
for mode in filter empty-filter registration no-correspondence; do
    "$tests/pcl-contract" "$mode" > "$out/first/$mode.log" 2>&1
done
for mode in surface segmentation empty; do
    "$tests/pcl-expanded-contract" "$mode" > "$out/first/expanded-$mode.log" 2>&1
done
for mode in filter empty-filter registration; do
    "$tests/ember-pcl-cloud" --case "$mode" --output "$out/first/$mode.csv" > "$out/first/$mode.stdout" 2> "$out/first/$mode-example.log"
    [ ! -s "$out/first/$mode.stdout" ]
    "$tests/check-pcl-csv" --case "$mode" --input "$out/first/$mode.csv" > "$out/first/$mode-check.log" 2>&1
    "$tests/ember-pcl-cloud" --case "$mode" --output - > "$out/first/$mode-stdout.csv" 2> "$out/first/$mode-stdout.log"
    cmp "$out/first/$mode.csv" "$out/first/$mode-stdout.csv"
done
for bad in 10 nan inf -inf; do
    sed "s/^registration,matrix,0,[^,]*/registration,matrix,0,$bad/" "$out/first/registration.csv" > "$out/controls/wrong-$bad.csv"
    status=0
    "$tests/check-pcl-csv" --case registration --input "$out/controls/wrong-$bad.csv" > "$out/controls/wrong-$bad.log" 2>&1 || status=$?
    [ "$status" = 1 ]
done
echo 'PASS: known centroids, ICP motion, independent CSV, compression and generic atomics'
expect()
{
    expected=$1 name=$2; shift 2
    status=0
    "$tests/ember-pcl-cloud" "$@" > "$out/controls/$name.stdout" 2> "$out/controls/$name.log" || status=$?
    echo "$status" > "$out/controls/$name.status"
    [ "$status" = "$expected" ]
}
expect 65 no-correspondence --case no-correspondence --output "$out/controls/rejected.csv"
[ ! -e "$out/controls/rejected.csv" ]
printf 'preserve\n' > "$out/controls/preserved.csv"
expect 65 preserve-existing --case no-correspondence --output "$out/controls/preserved.csv"
[ "$(cat "$out/controls/preserved.csv")" = preserve ]
expect 64 invalid-option --unknown
expect 64 missing-value --output
expect 74 missing-directory --case filter --output "$out/missing/cloud.csv"
expect 74 output-directory --case filter --output "$out/controls"
[ -e /dev/full ]
expect 74 full-output --case filter --output /dev/full
status=0
"$tests/ember-pcl-cloud" --case filter --output - > /dev/full 2> "$out/controls/full-stdout.log" || status=$?
echo "$status" > "$out/controls/full-stdout.status"
[ "$status" = 74 ]
for name in test_common test_pointcloud test_transforms test_filters_grid_minimum test_morphological test_filters_functor test_uniform_sampling test_warps test_correspondence_estimation test_registration test_kdtree_search test_flann_search test_concave_prism test_ear_clipping; do
    status=0
    if [ "$name" = test_ear_clipping ]; then
        "$tests/upstream/$name" "$tests/data/bun0.pcd" > "$out/upstream/$name.log" 2>&1 || status=$?
    elif [ "$name" = test_registration ]; then
        "$tests/upstream/$name" "$tests/data/bun0.pcd" "$tests/data/bun4.pcd" "$tests/data/milk_color.pcd" > "$out/upstream/$name.log" 2>&1 || status=$?
    else
        "$tests/upstream/$name" > "$out/upstream/$name.log" 2>&1 || status=$?
    fi
    echo "$status" > "$out/upstream/$name.status"
    [ "$status" = 0 ] || { cat "$out/upstream/$name.log" >&2; exit 1; }
    echo "PASS: $name"
done
for name in eigen3 boost-headers boost-libs compiler-rt lz4 flann-lib; do
    status=0
    pkg_delete "$name" > "$out/$name-delete-protected.log" 2>&1 || status=$?
    [ "$status" -ne 0 ]
    pkg_info -e "$name" > /dev/null
done
for name in pcl flann-lib lz4 compiler-rt boost-libs boost-headers eigen3; do
    pkg_delete "$name" >> "$out/remove.log" 2>&1
    if pkg_info -e "$name" > /dev/null 2>&1; then exit 1; fi
done
for library in /usr/pkg/lib/libpcl_common.so /usr/pkg/lib/libpcl_surface.so /usr/pkg/lib/libpcl_segmentation.so /usr/pkg/lib/libpcl_ml.so /usr/pkg/lib/libpcl_registration.so /usr/pkg/lib/libflann_cpp.so /usr/pkg/lib/liblz4.so /usr/pkg/lib/libboost_iostreams.so /usr/pkg/lib/libboost_random.so /usr/pkg/gcc16/lib/libatomic.so; do
    [ ! -e "$library" ] && [ ! -L "$library" ]
done
install_packages > "$out/reinstall.log" 2>&1
for mode in filter empty-filter registration; do
    "$tests/ember-pcl-cloud" --case "$mode" --output "$out/reinstalled/$mode.csv" > "$out/reinstalled/$mode.stdout" 2> "$out/reinstalled/$mode.log"
    "$tests/check-pcl-csv" --case "$mode" --input "$out/reinstalled/$mode.csv" > "$out/reinstalled/$mode-check.log" 2>&1
    cmp "$out/first/$mode.csv" "$out/reinstalled/$mode.csv"
done
for mode in surface segmentation empty; do
    "$tests/pcl-expanded-contract" "$mode" > "$out/reinstalled/expanded-$mode.log" 2>&1
done
for name in $all; do pkg_admin check "$name" > "$out/$name-reinstalled-integrity.log" 2>&1; done
pkg_info -a > "$out/packages.txt"
echo 'PASS: installed PCL filtering, registration, dependencies and package lifecycle'
