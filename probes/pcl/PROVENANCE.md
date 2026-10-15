# PCL package provenance

Official releases, tags and source archives were checked on 2026-10-15.
Hashes remain in the canonical recipe `distinfo` files and the source lists.
Archives are downloaded from their original upstream providers.

| Source | Revision or release | License and owner |
|---|---|---|
| [PCL 1.15.1](https://github.com/PointCloudLibrary/pcl/releases/tag/pcl-1.15.1) | `3346843ea6b97697a1577293aa9cdf236b5c7ffb` | BSD-3-Clause; Willow Garage, Open Perception and contributors |
| [FLANN 1.9.2](https://github.com/flann-lib/flann/tree/1.9.2) | `c50f296b0b27e14667d272b37acc63f949b305c4` | BSD-3-Clause; Marius Muja, David G. Lowe and contributors |
| [LZ4 1.10.0](https://github.com/lz4/lz4/releases/tag/v1.10.0) | `ebb370ca83af193212df4dcbadcc5d87bc0de2f0` | BSD-2-Clause library; GPL-2.0-or-later CLI; Yann Collet and contributors |
| [Boost 1.92.0](https://github.com/boostorg/boost/releases/tag/boost-1.92.0) | Official `boost-1.92.0-cmake.tar.xz` release archive | Boost Software License 1.0; individual library authors |
| [Eigen 5.0.1](../../pkgsrc/local-robotics/eigen3/files/SOURCE) | `bc3b39870ecb690a623a3f49149a358b95c5781d` | MPL-2.0 with upstream per-file notices |
| [GCC 16.2.0](../../pkgsrc/local-robotics/gcc16-libatomic/files/SOURCE) | Official `gcc-16.2.0.tar.xz`; atomic runtime component | GPL-3.0-or-later with GCC Runtime Library Exception 3.1 |
| [GoogleTest 1.18.0](https://github.com/google/googletest/releases/tag/v1.18.0) | `063de7e9578f82b369302001269680b4b1553359` | BSD-3-Clause; Google and contributors; test-only source |

PCL, LZ4 and Boost use the current stable releases checked for this task.
FLANN 1.9.2 is its latest upstream release tag; the upstream project has no
newer stable tag. Its age does not select another compiler or a parallel
older dependency set.

The common Eigen and Boost providers retain their existing versions and
header namespaces. `boost-libs` supplies the already established Serialization
closure. The new `boost-iostreams` package adds Iostreams and its required
compiled Random component. It also owns the new header-only Dynamic Bitset
CMake exports. Existing common header exports are not replaced. Random-device
support remains enabled. Base OS zlib, bzip2 and lzma support remains enabled;
Zstd is outside the selected profile.

The atomic component supplies files missing from the partial GCC16 cross SDK.
It uses the same current GCC source and runtime version. Complete GCC16
packages retain ownership of their runtime; the standalone component conflicts
with those providers.

PCL retains its embedded KissFFT, LZF and PLY implementations. Package license
files preserve Mark Borgerding's KissFFT notices, Marc Alexander Lehmann's LZF
notices, Willow Garage notices and representative PLY source attribution.
The expanded profile also retains Poisson4 geometry attribution to Michael
Kazhdan and Matthew Bolitho, SVM attribution to Chih-Chung Chang and Chih-Jen
Lin, and the PCL ML source notices. Representative source files accompany
the package. Installed upstream headers retain their own notices.
The LZ4 package preserves both the BSD library license and the GPL CLI license. These licenses do not
change the ownership or licensing of the EmberBSD checks.

## Canonical source adaptations

- [PCL Eigen dependency](../../pkgsrc/local-robotics/pcl/patches/patch-eigen5)
  updates both build-time and exported `find_package` requests to exact Eigen
  5.0.1. Eigen's own version policy remains intact. Eigen does not masquerade
  as version 3.x.
- [PCL FLANN relocation](../../pkgsrc/local-robotics/pcl/patches/patch-relocatable-flann)
  replaces the configured cross-sysroot fallback with the installed PCL
  prefix. Explicit caller roots and the all-in-one installer layout remain
  supported. An isolated installed-config probe catches the original
  build-host fallback assignment and accepts the relocated form.
- [PCL caller RPATH](../../pkgsrc/local-robotics/pcl/patches/patch-cmake-rpath)
  honors an explicit `CMAKE_BUILD_WITH_INSTALL_RPATH` setting. The upstream
  unconditional `FALSE` discarded the caller setting, so cross-built test
  programs could not load installed PCL libraries in the guest. The default
  remains `FALSE` when the caller provides no value. The patch changes build
  configuration behavior; it does not change PCL algorithms.
- [FLANN dependency metadata](../../pkgsrc/local-robotics/flann/patches/patch-lz4-target)
  uses the common imported `LZ4::lz4` target and exports `find_dependency(lz4)`.
  Its pkg-config file requests `liblz4` and only the selected FLANN libraries.
  The original install retained absolute cross-sysroot links and an absent C
  binding. FLANN's C++ algorithms are unchanged.
- [LZ4 zero-length buffers](../../pkgsrc/local-robotics/lz4/patches/patch-zero-buffers)
  fixes confirmed null-pointer arithmetic in the frame decoder. Repeated
  frame-info queries call this path internally. The change preserves null
  output-buffer semantics and dictionary ownership. The regression checks
  empty operations, repeated queries, pending output and four complete frame
  round trips. Fatal UBSan confirms the original failure and the corrected
  behavior on the native control platform.
- [FLANN test ownership](../../pkgsrc/local-robotics/pcl/patches/patch-flann-test-ownership)
  passes an owning index-creator pointer in the correct constructor argument.
  The original raw pointer converted to the leading boolean and leaked.
  This fixes seven upstream test calls without changing the library API or
  algorithms. Full native Memcheck reproduces five leaked allocations in
  the original program; the corrected program retains all five test cases.

These local adaptations were written with AI assistance for EmberBSD Ports.
They have not been submitted or accepted upstream. Boost and libatomic have
no source patches in this profile. FLANN's CMake compatibility floor is set
to 3.5 for current tools; upstream diagnostics remain enabled.

The canonical
[PCL features](../../pkgsrc/local-robotics/pcl/features.cmake) build ten shared
libraries plus the `2d` header component. Expanded RTAB-Map surface and
segmentation modules are outside this package profile. Build and runtime
results must name their actual profile, compiler, platform and test scope.

The probes and consumer checks use the MIT [license](LICENSE). Individual
package recipes and helpers carry their own SPDX identifiers. They do not
relicense upstream source. Source lists are [PCL](sources.tsv),
[common dependency additions](cross/dependency-sources.tsv) and
[test-only GoogleTest](test-sources.tsv).

## Expanded shared profile

Package revision `pcl-1.15.1nb1` retains the same pinned upstream source and
canonical patches. It adds Surface, Segmentation and compiled ML, plus the
header-only Geometry subsystem. The existing `2d` subsystem remains header-only.
The shared-library count grows from ten to thirteen. External providers,
core point types and the disabled GUI/sensor/Qhull/OpenMP features stay fixed.

The expanded installed contract uses the RGB-to-RGB-normal MLS combination
required by RTAB-Map. Its plane and normal oracle is independent of the PCL
output. The segmentation oracle checks a known plane and three outliers.
Upstream `test_concave_prism` and `test_ear_clipping` extend the bounded
selection to fourteen programs. The latter uses the pinned `bun0.pcd` fixture.
Expanded runtime results belong in [validation](VALIDATION.md).

The expanded Linux control reuses the accepted same-version native dependency
builds. CMake relocates their ELF runtime paths to the current prefix without
changing code or SONAMEs. PCL itself is rebuilt from the pinned source for
all thirteen libraries. Target DSOs do not enter the native control prefix.
