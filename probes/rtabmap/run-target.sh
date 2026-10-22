#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed recorded-image map acceptance.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
all='eigen3 boost-headers boost-libs gcc16-libatomic lz4 flann boost-iostreams pcl gtsam png libjpeg-turbo sqlite3 opencv5 rtabmap'
for name in $all; do
    if pkg_info -e "$name" >/dev/null 2>&1; then echo "Preserve installed package: $name" >&2; exit 2; fi
done
mkdir -p "$out/first" "$out/reinstalled" "$out/upstream" "$out/controls"
install_packages()
{
    for package in eigen3-5.0.1 boost-headers-1.92.0 boost-libs-1.92.0 gcc16-libatomic-16.2.0 lz4-1.10.0 flann-1.9.2 boost-iostreams-1.92.0 pcl-1.15.1nb1 gtsam-4.3.0 png-1.6.59 libjpeg-turbo-3.2.0nb2 sqlite3-3.54.1 opencv5-5.0.0 rtabmap-0.23.8; do
        pkg_add "$packages/$package.tgz"
    done
}
install_packages > "$out/install.log" 2>&1
for name in $all; do
    pkg_admin check "$name" > "$out/$name-integrity.log" 2>&1
    pkg_info -B "$name" > "$out/$name-build-info.txt"
done
for binary in rtabmap-contract ember-rtabmap-recorded-map check-recorded-map pcl-expanded-contract; do
    ldd "$tests/$binary" > "$out/$binary-linkage.txt"
    grep -F /usr/pkg/gcc16/lib/libstdc++.so.7 "$out/$binary-linkage.txt" >/dev/null
    if grep -E 'not found|/workspace/|libgomp|libvtk|libQt|libpython|libc\+\+' "$out/$binary-linkage.txt"; then exit 1; fi
done
for library in librtabmap_core libopencv_core libsqlite3 libgtsam libpcl_surface libpcl_segmentation; do
    grep -F "/usr/pkg/lib/$library.so" "$out/ember-rtabmap-recorded-map-linkage.txt" >/dev/null
done
for mode in filter empty-filter registration no-correspondence; do
    "$tests/pcl-contract" "$mode" > "$out/first/pcl-$mode.log" 2>&1
done
for mode in surface segmentation empty; do
    "$tests/pcl-expanded-contract" "$mode" > "$out/first/pcl-$mode.log" 2>&1
done
"$tests/opencv-foundations" > "$out/first/opencv-foundations.log" 2>&1
"$tests/image-codecs-contract" > "$out/first/image-codecs.log" 2>&1
"$tests/sqlite-consumer" "$out/first/sqlite" > "$out/first/sqlite.log" 2>&1
for name in thread-state natural-join thread-join private-flann; do
    "$tests/$name" > "$out/first/$name.log" 2>&1
done
for mode in default gtsam; do
    "$tests/rtabmap-lifecycle" "$mode" > "$out/first/lifecycle-$mode.log" 2>&1
done
"$tests/private-lz4" /usr/pkg/lib/librtabmap_core.so /usr/pkg/lib/libflann_cpp.so \
    /usr/pkg/lib/liblz4.so > "$out/first/private-lz4.log" 2>&1
"$tests/opencv-plugin-loader" "$tests/libopencv-loader-fixture.so" > "$out/first/opencv-plugin-loader.log" 2>&1
for mode in data-vector data-mat data-read rvl-vector rvl-mat; do
    "$tests/compression-roundtrip" "$mode" > "$out/first/compression-$mode.log" 2>&1
done
sh "$tests/codecs/run-tests.sh" "$tests/codecs" "$out/codecs" > "$out/first/codec-tests.log" 2>&1
sh "$tests/opencv-upstream/run.sh" "$tests/opencv-upstream/opencv-core-upstream" \
    "$out/opencv-upstream" > "$out/first/opencv-upstream.log" 2>&1
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
done
mapping()
{
    pass=$1
    "$tests/rtabmap-contract" "$out/$pass/analytic.db" > "$out/$pass/rtabmap.log" 2>&1
    "$tests/ember-rtabmap-recorded-map" --dataset "$tests/recorded-fixture" --output "$out/$pass/recorded" > "$out/$pass/recorded.log" 2>&1
    "$tests/check-recorded-map" --dataset "$tests/recorded-fixture" --results "$out/$pass/recorded" > "$out/$pass/check-recorded.log" 2>&1
}
mapping first
expect()
{
    expected=$1 name=$2; shift 2
    status=0
    "$@" > "$out/controls/$name.stdout" 2> "$out/controls/$name.log" || status=$?
    echo "$status" > "$out/controls/$name.status"
    [ "$status" = "$expected" ]
}
expect 64 unknown "$tests/ember-rtabmap-recorded-map" --unknown
expect 65 missing "$tests/ember-rtabmap-recorded-map" --dataset "$tests/missing" --output "$out/controls/missing-output"
[ ! -e "$out/controls/missing-output" ]
expect 74 preserved "$tests/ember-rtabmap-recorded-map" --dataset "$tests/recorded-fixture" --output "$out/first/recorded"
"$tests/check-recorded-map" --dataset "$tests/recorded-fixture" --results "$out/first/recorded" > "$out/controls/preserved-recheck.log" 2>&1
cp -R "$out/first/recorded" "$out/controls/corrupt"
sed '2s/[^,]*/nan/' "$out/controls/corrupt/cloud.csv" > "$out/controls/bad.csv"
mv "$out/controls/bad.csv" "$out/controls/corrupt/cloud.csv"
expect 1 corrupt-export "$tests/check-recorded-map" --dataset "$tests/recorded-fixture" --results "$out/controls/corrupt"
for name in sqlite3 opencv5 pcl gtsam png libjpeg-turbo eigen3; do
    status=0
    pkg_delete "$name" > "$out/$name-delete-protected.log" 2>&1 || status=$?
    [ "$status" -ne 0 ]
    pkg_info -e "$name" >/dev/null
done
for name in rtabmap opencv5 sqlite3 libjpeg-turbo png gtsam pcl boost-iostreams flann lz4 gcc16-libatomic boost-libs boost-headers eigen3; do
    pkg_delete "$name" >> "$out/remove.log" 2>&1
    if pkg_info -e "$name" >/dev/null 2>&1; then exit 1; fi
done
for path in lib/librtabmap_core.so lib/libopencv_core.so lib/libsqlite3.so lib/libpcl_surface.so lib/libpcl_segmentation.so lib/libgtsam.so lib/libpng16.so lib/libjpeg.so include/sqlite3.h; do
    [ ! -e "/usr/pkg/$path" ] && [ ! -L "/usr/pkg/$path" ]
done
install_packages > "$out/reinstall.log" 2>&1
mapping reinstalled
for file in poses.csv cloud.csv map.ply; do
    cmp "$out/first/recorded/$file" "$out/reinstalled/recorded/$file"
done
for name in $all; do pkg_admin check "$name" > "$out/$name-reinstalled-integrity.log" 2>&1; done
pkg_info -a > "$out/packages.txt"
echo 'PASS: recorded RGB-D map, reopened database, independent point geometry and fourteen real package lifecycles'
