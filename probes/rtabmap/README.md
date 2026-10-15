# RTAB-Map recorded-data mapping

The shared, headless **RTAB-Map 0.23.8** profile uses GCC 16.2.0 and the common
Eigen 5.0.1, Boost 1.92.0, OpenCV 5.0.0, PCL 1.15.1nb1, GTSAM 4.3.0,
SQLite 3.54.0, PNG 1.6.59 and libjpeg-turbo 3.2.0nb2 providers.
The [canonical package](../../pkgsrc/local-robotics/rtabmap) installs the core
and utilite shared libraries, headers, relocatable CMake exports and notices.
See [provenance](PROVENANCE.md), [validation](VALIDATION.md),
[source pin](sources.tsv) and [license](LICENSE).

The [recorded-map example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/rtabmap-recorded-map)
imports twelve unchanged RGB/depth PNG pairs from TUM RGB-D `fr1/desk`, inserts
their recorded poses, saves a SQLite database, closes and reopens it, and
exports poses and a colored point cloud. A separate checker uses PNG, SQLite
and independent camera/quaternion arithmetic to check the exports.
This is mapping with supplied poses; it does not estimate camera motion.
The original recording is CC-BY-4.0 and is downloaded separately.

## Cross build

Use the fork's coherent AArch64 base sysroot and GCC16 C/C++ runtime. Install
the exact dependency payloads into a writable copy of the common sysroot.
The OpenCV [recorded-image provider](../../pkgsrc/local-robotics/opencv5)
builds thirteen shared libraries, including its `flann` and `objdetect` closure.
The PCL provider adds `surface`, `segmentation` and `ml` to the earlier profile;
`geometry` and `2d` are header-only. [Codec helpers](codecs/README.md) reuse the
canonical PNG and pinned pkgsrc JPEG recipes. Base zlib remains the provider.

RTAB-Map generates database schema resources while building. Build the real
upstream resource generator for the host first; an AArch64 executable cannot
perform that step on the Linux host.

```sh
sh probes/rtabmap/build-resource-tool.sh /absolute/rtabmap-0.23.8.tar.gz /absolute/new-host-tool
CROSS_JOBS=2 sh probes/rtabmap/cross-build.sh /absolute/gcc-prefix /absolute/sysroot \
  /absolute/rtabmap-0.23.8.tar.gz /absolute/new-host-tool/build/bin/rtabmap-res_tool \
  /absolute/new-cross-work
```

The cross builder verifies the archive, applies every canonical patch without
fuzz, records the actual compilation database, and checks the two AArch64 DSOs
and installed CMake exports for build-host paths. It stages under `/usr/pkg`.
The native resource generator is a build dependency and is not installed in
the selected library package. `RTABMAP_NATIVE_RES_TOOL` supplies it to pkgsrc
when `USE_CROSS_COMPILE=yes`.

## Native control and target acceptance

```sh
JOBS=1 sh probes/rtabmap/build.sh /absolute/common-prefix /absolute/new-native-work /absolute/archive-cache
sh probes/rtabmap/test.sh /absolute/new-native-work /absolute/patched-opencv-source
sh probes/rtabmap/run-target.sh /absolute/packages /absolute/target-tests /absolute/new-results
```

The first two commands require native EmberBSD/NetBSD and the exact installed
dependencies. The target runner requires EmberBSD AArch64 and a disposable
package database. It installs fourteen real packages, checks loaded libraries,
runs the analytic and recorded mapping scenarios, protects dependencies from
premature deletion, removes all packages, reinstalls them and repeats mapping.
It also runs the selected PCL, OpenCV, PNG/JPEG and SQLite checks and the local
thread, dynamic-loader, compression and private-index regressions.

The analytic contract generates six views with deterministic feature identities,
then reopens the map for localization. A known view must recover its 20 cm
world position despite a 25 cm supplied pose error. Empty observations must
not produce recognition, and read-only localization must not grow the database. This isolates
mapping, persistence and localization from feature detection. The recorded
example additionally exercises real ORB features and PNG database storage.

GTSAM is the graph solver. Qt, ROS, OpenMP, device capture, Python bindings and
optional GPL/noncommercial algorithms are disabled. OpenCV's upstream build
does use Python for code generation. The bundled utilite remains LGPL-3.0-or-later;
the package is not an all-BSD stack. Native memory analysis and target QEMU
execution are separate checks. Physical sensors, calibration, autonomous
navigation, long-running map growth and real-time performance remain untested.
