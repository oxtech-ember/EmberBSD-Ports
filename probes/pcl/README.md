# PCL filtering, registration and mapping geometry

Point Cloud Library (PCL) 1.15.1 filters point clouds and recovers rigid motion
with iterative closest point registration. PCL owns the algorithms. EmberBSD
Ports owns the GCC16 package recipes, dependency adaptations and acceptance
checks. The [point-cloud example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/pcl-cloud)
uses the common shared libraries.

The initial ten-library package passes installed acceptance in EmberBSD AArch64
QEMU. The current `pcl-1.15.1nb1` profile adds shared Surface, Segmentation and
ML for offline mapping. Its expanded target acceptance is pending. See
[validation](VALIDATION.md) for the measured scope and limitations.

## Common package set

Use GCC 16.2.0 and one coherent EmberBSD AArch64 sysroot. Keep the fork's
headers, libc and compiler runtime together. The acceptance package set is:

| Package | Role |
|---|---|
| [eigen3 5.0.1](../../pkgsrc/math/eigen3) | Common Eigen headers and CMake interface |
| boost-headers 1.92.0 (`devel/boost-headers`) | The common Boost headers |
| boost-libs 1.92.0 (`devel/boost-libs`) | The common compiled Boost libraries, including Iostreams, Random and Serialization |
| [gcc16-libatomic 16.2.0](../../pkgsrc/local-robotics/gcc16-libatomic) | Missing atomic component in a partial cross SDK |
| [lz4 1.10.0](../../pkgsrc/archivers/lz4) | Shared/static compression library and current CLI |
| [flann-lib 1.9.2](../../pkgsrc/math/flann-lib) | Shared/static CPU C++ nearest-neighbor search |
| [pcl 1.15.1nb1](../../pkgsrc/graphics/pcl) | Thirteen selected shared libraries and installed headers |

The standalone atomic package extends an incomplete GCC16 runtime. It conflicts
with complete `gcc16` and `gcc16-libs` providers. A complete runtime keeps
ownership of its own `libatomic`; it needs no second component package.

The installed PCL configuration requests Boost System, Iostreams and
Serialization. System is header-only in Boost 1.92.0. The common `boost-libs`
package supplies Serialization, Iostreams, Random and their compiled closure,
with the zlib, bzip2, lzma and zstd Iostreams backends. No private Eigen, Boost or OpenCV copy is introduced.

## Cross build

Use a new task copy of the common sysroot. It must already contain Eigen,
the common `boost-headers` and `boost-libs` packages and the GCC16 runtime. Use the original archives
listed in [sources.tsv](sources.tsv), [dependency sources](cross/dependency-sources.tsv)
and [test sources](test-sources.tsv).

If the SDK lacks `libatomic.so.3`, first use the common
[atomic component helper](../../profiles/development-toolchain/cross/build-libatomic.py).
Its recipe documents the source hash, staging layout and collision boundary.
Import only its verified missing stage into the task sysroot.

```sh
CROSS_JOBS=3 sh probes/pcl/cross/build-dependencies.sh \
  /absolute/gcc16-prefix /absolute/task-sysroot \
  /absolute/flann-1.9.2.tar.gz /absolute/lz4-1.10.0.tar.gz \
  /absolute/new-dependencies

CROSS_JOBS=3 sh probes/pcl/cross-build.sh \
  /absolute/gcc16-prefix /absolute/task-sysroot \
  /absolute/pcl-1.15.1.tar.gz /absolute/googletest-1.18.0.tar.gz \
  /absolute/new-pcl
```

The dependency helper stages three packages and adds them to the task sysroot
only after collision checks. It does not replace different existing files.
The PCL helper applies canonical recipe patches, builds the selected libraries
and fourteen upstream test programs, stages the install and builds independent
consumers. Both helpers verify source archives before extraction and reject
existing output paths. Logs, compilation databases, ELF records and input
hashes remain under each output directory.

The canonical [feature file](../../pkgsrc/graphics/pcl/features.cmake)
selects `common`, `kdtree`, `octree`, `search`, `sample_consensus`, `filters`,
`features`, `registration`, `io`, `surface`, `segmentation` and compiled `ml`.
PCL also builds `io_ply`; `2d` and `geometry` are header-only. This produces
thirteen shared libraries. The profile uses C++17, portable Armv8-A code and the upstream core point-type instantiations.
Other point types may need client-side instantiation.

GUI/VTK/Qt, sensor backends, OpenNI, CUDA, OpenMP, PNG, Qhull, applications
and tools are disabled. Optional surface NURBS support remains disabled.
Optional nanoflann does not remove PCL 1.15.1's FLANN requirement for the selected components.

## Native source helper

On EmberBSD, use the same complete common dependency prefix and GCC16:

```sh
JOBS=1 sh probes/pcl/build.sh /absolute/common-prefix \
  /absolute/new-pcl-work /absolute/archive-cache
sh probes/pcl/test.sh /absolute/new-pcl-work
```

Omit the cache argument to download the pinned PCL source. The native helper
uses the same canonical recipe features and patches. It does not build another
FLANN or Boost. `JOBS` defaults to one. Optional positive `BUILD_AS_KIB` sets
and verifies a soft compiler address-space limit while preserving the hard
limit. The cross route supplies the target acceptance artifacts; a complete
native EmberBSD source-package build needs separate evidence.

## Installed contracts and target acceptance

The independent CMake project checks exact dependency versions, canonical
imported library locations and the selected GCC16 runtime.

| Case | Independent expected outcome |
|---|---|
| `filter` | Range filtering removes a distant point and NaN; voxel centroids are `(0.2,0.2,0.2)` and `(1.2,0.2,0.2)` |
| `empty-filter` | Empty input produces empty range and voxel outputs |
| `registration` | ICP recovers a `0.012` radian Z rotation and translation `(0.04,-0.03,0.02)` within `1e-4` |
| `no-correspondence` | Distant clouds with a bounded correspondence radius do not report convergence |
| `surface` | MLS preserves an 81-point analytic plane, RGB values and its known unit normals |
| `segmentation` | RANSAC recovers all 49 analytic plane points, excludes three outliers and matches the plane equation |
| `empty` | Surface and segmentation return empty output for empty input |
| `matrix-check` | The comparison predicate rejects NaN and both infinities in every matrix coefficient |
| `lz4-zero-buffers` | Repeated frame queries and zero-length operations preserve four full frame round trips |
| `boost-iostreams-contract` | zlib, gzip, bzip2 and lzma round trips match every byte; the Random device API works |

The new `pcl-expanded-contract` executable runs `surface`, `segmentation` and
`empty`. MLS uses `PointXYZRGB` input and `PointXYZRGBNormal` output, matching
the shared RTAB-Map consumer. The core point-type library instantiates this
combination. This check is separate from a complete RTAB-Map build.

Registration checks all sixteen transform coefficients, the final fitness and
every transformed point. The target runner also checks the Examples CLI and
its independent CSV checker, invalid inputs, output errors, fourteen upstream
programs and real package removal/reinstallation. GoogleTest is a source-based
test dependency; it is not part of the runtime package set.

```sh
sh probes/pcl/run-target.sh /absolute/packages /absolute/tests \
  /absolute/new-results
```

The runner requires an AArch64 EmberBSD guest with the prepared eight packages
absent. It preserves existing installations and records actual package and
program exit statuses. Its fixture directory contains the cross-built
consumers, upstream programs and pinned source data prepared by the acceptance
harness. Do not count a skipped or incomplete guest run as a pass.

The [cross input guards](tests/cross-guards.sh) and
[dependency guards](cross/test-dependency-guards.sh) check damaged archives,
output preservation, invalid job counts and complete collision preflight.
They establish input handling, separate from runtime behavior.

The [RPATH regression](tests/rpath-setting.rb) checks the actual upstream
CMake block against explicit ON/OFF and default settings before and after
the source patch. It also requires zero-fuzz, zero-offset patch application.

These software fixtures do not validate a depth camera or LiDAR, calibration,
visualization, real-time deadlines or sustained board operation. See
[provenance](PROVENANCE.md) for source pins, licenses and adaptation ownership.
