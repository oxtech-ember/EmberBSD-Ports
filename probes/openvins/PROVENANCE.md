# OpenVINS source provenance

Checked against primary upstream metadata on 2026-10-07.

- [OpenVINS v2.7](https://github.com/rpng/open_vins/releases/tag/v2.7) is the latest
  non-prerelease GitHub release, published 2023-06-20. Pin:
  `93adc241390d13e99232652cf05cbe18a93c7bea`.
- [Upstream master](https://github.com/rpng/open_vins/commit/69488123ed9362dd44b6f28e7f4680abbff1442b)
  was last updated 2025-11-30 in the checked response. The stable release is older
  than that work; this recipe backports the accepted Ceres compatibility change.
- [Archive](https://codeload.github.com/rpng/open_vins/tar.gz/93adc241390d13e99232652cf05cbe18a93c7bea):
  SHA256 `aa7be7b18824dc53af4ae79ca3c771c721b7b0951a0cd9ee874f04034358033e`;
  142,632,081 bytes. Full extraction is about 398 MiB, including 376 MiB of
  unused `ov_data`. The recipe extracts only estimator, core, initialization,
  configuration and license/readme members. It does not need dataset downloads.

## Licenses and shared dependencies

OpenVINS source headers specify GPL-3.0-or-later, retaining Patrick Geneva,
Guoquan Huang, Kevin Eckenhoff and the OpenVINS contributors. The original
`LICENSE` is installed. Optional matplotlibcpp has its own MIT notice; plotting,
ROS and ArUco are disabled here. Our original shell/C++ checks are MIT licensed;
patches to upstream files retain their upstream license and attribution.

Dependencies are the existing common Eigen 5.0.1 (MPL-2.0 and file exceptions),
OpenCV 5.0.0 (Apache-2.0), Boost 1.92.0 (BSL-1.0) and Ceres 2.2.0 (BSD-3-Clause).
[Official Ceres tags](https://github.com/ceres-solver/ceres-solver/tags) identify
2.2.0, commit `85331393dc0dff09f6fb9903ab0c4bfa3e134b01`, as current stable in the
checked source; reuse [the existing recipe](../ceres/PROVENANCE.md). Do not create
an older Ceres/Eigen/OpenCV installation to satisfy the old OpenVINS CMake logic.

## Patches

`ceres-manifold-upstream.patch` is unchanged from accepted upstream commit
[676042f779c9146ee3612ea74f05a29a3d5d317d](https://github.com/rpng/open_vins/commit/676042f779c9146ee3612ea74f05a29a3d5d317d),
author omer, 2025-08-07. It adds the Ceres 2.2 Manifold path to
`State_JPLQuatLocal`; the original author and commit remain in the patch header.
[Original patch](https://github.com/rpng/open_vins/commit/676042f779c9146ee3612ea74f05a29a3d5d317d.patch)
SHA256: `888050ceaef7c6a5f5f43f0ca4d829648b1f34bb45ee585a967ab5f566dac811`.

`shared-dependencies.patch` is local, AI-assisted source preparation. It selects
exact common versions, C++17, Eigen/Ceres imported targets and Boost's current
filesystem/thread/date_time components (system is header-only). It removes
forced `-O3`, unrolling and debug flags so the caller controls resource use.
It substitutes OpenCV 5's `features.hpp` and removes unused highgui includes
from core tracking headers. No tracker, estimator or missing API is stubbed.
These local changes have not been submitted upstream or natively validated.
