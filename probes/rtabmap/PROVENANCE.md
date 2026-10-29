# RTAB-Map source provenance

Official release metadata was checked on 2026-10-15.

| Item | Pinned source |
|---|---|
| Generic stable release | [RTAB-Map 0.23.8](https://github.com/introlab/rtabmap/releases/tag/0.23.8), published 2026-07-05 |
| Commit | [`d069becc724905d6465a8758c40dae88e13bb9e8`](https://github.com/introlab/rtabmap/commit/d069becc724905d6465a8758c40dae88e13bb9e8) |
| Archive | [Original commit archive](https://codeload.github.com/introlab/rtabmap/tar.gz/d069becc724905d6465a8758c40dae88e13bb9e8) |
| SHA256 | `587d8936b8d8669b196d500df80e373417e0c4c033309a2e4a0b84a627117284` |
| Size | 22,276,030 bytes |

Newer `0.23.13-*` tags identify ROS distribution releases. This ROS-free core
uses the latest generic stable release checked for the task. The canonical
[package](../../pkgsrc/local-robotics/rtabmap), its
[distinfo](../../pkgsrc/local-robotics/rtabmap/distinfo) and
[source list](sources.tsv) define the selected inputs.

## Ownership and licenses

The main code is BSD-3-Clause, Mathieu Labbe, IntRoLab/Universite de Sherbrooke
and contributors. Bundled utilite is LGPL-3.0-or-later under its file notices.

The RVL codec wrapper credits Andrew D. Wilson, Fast Lossless Depth Image
Compression, SIGCHI 2017, and declares MIT licensing. The package installs
the [MIT permission text](../../pkgsrc/local-robotics/rtabmap/licenses/MIT.txt)
and the original RVL header notice. All selected
license families and their original notices remain intact.

Our original shell/C/C++ checks are MIT. Patches to upstream files retain
those files' terms and authorship.

The private modified `rtflann` namespace contains BSD FLANN-derived code and
bundled BSD-2-Clause LZ4. Its private API and stream layouts are distinct from
the common public FLANN/LZ4 providers. It remains an internal implementation;
no second public FLANN/LZ4 package is installed. The package preserves the
individual source notices. Local symbol visibility keeps this private LZ4
from interposing the current shared LZ4 used by public FLANN and PCL.

The shared profile disables optional TORO, ORB-OCTREE, Madgwick, Vertigo and
unused GUI, device and Python backends. The selected graph solver is common
GTSAM 4.3.0. Eigen 5.0.1, Boost 1.92.0, OpenCV 5.0.0, PCL 1.15.1nb1 and
SQLite 3.54.0 retain their independent ownership and notices. The
[OpenCV recipe](../../pkgsrc/graphics/opencv) lists its image dependencies
and portability patches.

The unchanged GNU license texts were retrieved on 2026-10-07:

- [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.txt), SHA256
  `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.
- [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.txt), SHA256
  `e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118`.

## Canonical source adaptations

Builders apply the [package patch directory](../../pkgsrc/local-robotics/rtabmap/patches).
Older files under this probe's `patches/` directory remain historical source
material. They do not override the canonical package patches.

- [OpenCV 5 backport](../../pkgsrc/local-robotics/rtabmap/patches/patch-opencv5-upstream)
  selects core, top-level CMake and installed-config changes from accepted
  [PR 1732](https://github.com/introlab/rtabmap/pull/1732), merge commit
  [`d9f3337f978fffd9cf4b04bee15636bf00a2b870`](https://github.com/introlab/rtabmap/commit/d9f3337f978fffd9cf4b04bee15636bf00a2b870),
  by Mathieu Labbe, merged 2026-07-30. GUI/CI changes and the 0.23.9 version
  bump are omitted. The original complete patch has SHA256
  `a5aae59ec0684eef289a0ef514267ca99c5ddd6d7b9fc2a1c62de2504f3d6e22`.
  Upstream acceptance applies to the original change, not this local selection.
- [Shared dependencies](../../pkgsrc/local-robotics/rtabmap/patches/patch-shared-dependencies)
  requires the current common providers. Headless includes use imgcodecs and
  videoio while retaining real photo and stitching algorithms. The stable
  GTSAM 4.3.0 attitude-factor guard selects `AttitudeFactor<Pose3>`.
- [GTSAM optional values](../../pkgsrc/local-robotics/rtabmap/patches/patch-gtsam-optional)
  uses `std::optional::has_value()` with the selected GTSAM 4.3.0 API.
- [GTSAM dependency contract](../../pkgsrc/local-robotics/rtabmap/patches/patch-gtsam4-dependencies)
  removes unused filesystem/program_options/timer requirements for GTSAM 4.3.
  PCL keeps its actual Boost dependencies. Older GTSAM and libpointmatcher
  conditions retain their original dependency path.
- [Relocatable exports](../../pkgsrc/local-robotics/rtabmap/patches/patch-relocatable-exports)
  removes build-sysroot include paths from installed interfaces. Imported
  OpenCV/PCL targets propagate their own includes. The installed configuration
  resolves the same exact shared providers and the GTSAM dependent target.
- [Resource-tool install](../../pkgsrc/local-robotics/rtabmap/patches/patch-resource-tool-install)
  keeps the genuine resource generator available during native builds while
  omitting it from the library package with `BUILD_TOOLS=OFF`. Cross builds
  import the separately built native generator and do not install a host binary.
- [Compression alignment and RVL](../../pkgsrc/local-robotics/rtabmap/patches/patch-compression-alignment-rvl)
  reads and writes metadata through aligned objects and `memcpy`. RVL word
  arithmetic uses defined unsigned operations. A new byte-counted decoder
  rejects truncated or invalid runs while the legacy public overload remains.
  Recorded-depth decoding uses the bounded path. The
  [compression regression](tests/compression.cpp) covers the actual APIs.
- [Private LZ4 visibility](../../pkgsrc/local-robotics/rtabmap/patches/patch-private-lz4-symbols)
  hides the two bundled C implementations without hiding the public C++ API.
  This preserves the private backend and the current shared LZ4 provider.
- [Mutex destruction](../../pkgsrc/local-robotics/rtabmap/patches/patch-umutex-destruction)
  destroys an already unlocked POSIX mutex without unlocking it a second time.
- [Thread state](../../pkgsrc/local-robotics/rtabmap/patches/patch-uthread-atomic)
  publishes lifecycle state atomically and takes one snapshot in `isRunning()`.
  Size, alignment and lock-free assertions cover the selected GCC16 layouts.
- [Natural completion and self-join](../../pkgsrc/local-robotics/rtabmap/patches/patch-uthread-self-join)
  uses thread-local worker identity before acquiring the join lock. It avoids
  reading an OS handle that natural completion can reset concurrently.

The local adaptations, including the backport selection, were written with
AI assistance for EmberBSD Ports. No local adaptation has been submitted or
accepted upstream. The original OpenCV change has its separate upstream
acceptance credited above.

[Lifecycle ownership](../../pkgsrc/local-robotics/rtabmap/patches/patch-lifecycle-ownership)
releases `Memory`'s owned marker detector and the three default strategies
that `close()` recreates before final `Rtabmap` destruction. `close()` keeps
its reusable behavior. Strict Memcheck mapping and repeated init/close tests
identified and exercise these leaks; no API or class layout changes.

[Private KD-tree initialization](../../pkgsrc/local-robotics/rtabmap/patches/patch-private-kdtree-initialization)
initializes the leaf node split value that field-wise index serialization
always writes. This removes an uninitialized read in private LZ4HC compression;
it preserves the wire format and allocator behavior. A real saved-index
roundtrip checks the restored nearest-neighbor answers under Memcheck.

The threading changes cover lifecycle-state publication and the selected
natural-completion/self-join paths. Raw handle and ID getters require external
lifecycle synchronization. Object owners must coordinate start, kill, join
and destruction. Mutex owners must release their locks before destruction.
These changes do not establish general concurrent access to every utilite API.

[POSIX thread termination](../../pkgsrc/local-robotics/rtabmap/patches/patch-uthread-termination)
makes workers joinable and keeps their handles owned by the creator until
successful OS join. This waits for TLS destruction after the old mutex barrier;
the earlier detached-worker implementation could return before that cleanup.
Restart reaps a completed worker first. The TLS self identity also covers
thread-local destructors. Object fields, size, alignment and signatures remain
unchanged; raw handle/ID getters now retain a completed POSIX worker's identity
until join and still need external synchronization. Windows keeps its existing
behavior and was not executed. A gated TLS regression, repeated restart,
concurrent joiners and a real Linux child-only creation failure exercise the fix.

## Host tool and validation boundary

The native `local-robotics/rtabmap-res-tool` package builds genuine upstream
`rtabmap-res_tool` from Ports through the upstream resource-only branch.
`ANDROID_PREBUILD` names that branch; it does not set the Android target.
Cross code generation executes this native program. Native full builds retain
build-tree RPATHs so the generator can load the new utilite before installation.
Installed consumers use their final library paths.

Source adaptations, native controls and target acceptance are separate evidence.
The [validation record](VALIDATION.md) owns the measured results and limitations.
Recorded datasets are separate inputs with their own provenance and licenses.
