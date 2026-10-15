# OpenCV source provenance

Official release metadata was checked on 2026-10-15.

| Item | Pinned source |
|---|---|
| Stable release | [OpenCV 5.0.0](https://github.com/opencv/opencv/releases/tag/5.0.0), published 2026-06-06 |
| Commit | [`40738fb16ceddb5fb3fea747585f7ce6abb0605b`](https://github.com/opencv/opencv/commit/40738fb16ceddb5fb3fea747585f7ce6abb0605b) |
| Archive | [Original tag archive](https://github.com/opencv/opencv/archive/refs/tags/5.0.0.tar.gz) |
| SHA256 | `b0528f5a1d379d59d4701cb28c36e22214cc51cf64594e5b56f2d3e6c0233095` |
| Size | 81,594,270 bytes |

The canonical [distinfo](distinfo) records source and patch checksums.
The [source notice](files/SOURCE) accompanies installed packages.

## Ownership and licenses

OpenCV authors and contributors own the upstream implementation. Its main
license is Apache-2.0. The selected sources also retain BSD, MIT and font
license notices. The package installs the original main license and the
available third-party license files. Installed headers retain their notices.
External Eigen, PNG, JPEG and base zlib keep their own package ownership.

EmberBSD's recipe, helpers and local source adaptations are AI-assisted work.
Local OpenCV patches have not been submitted or accepted upstream. Their
upstream source terms remain in force. Package metadata does not relicense
OpenCV or its contributors' code.

## Canonical adaptations

- [AArch64 baseline](patches/patch-netbsd-arm64) enables the mandatory Advanced
  SIMD and half/single conversion features on the EmberBSD/NetBSD AArch64 ABI.
  Optional FP16 arithmetic, dot product, BF16 and SVE remain disabled without
  supported runtime detection. The selection follows the existing
  [robotics-foundations adaptation](../../../probes/robotics-foundations).
- [POSIX filesystem](patches/patch-netbsd-filesystem) selects OpenCV's existing
  Unix filesystem implementation on EmberBSD/NetBSD. It provides actual
  working-directory and directory operations required by recorded data.
  It carries the authorship of the earlier local media adaptation.
- [POSIX plugin loader](patches/patch-netbsd-plugin-loader) includes the
  platform in the existing `dlopen`, `dlsym` and `dlclose` branches. The previous
  guards left return paths absent and did not release loaded handles. The
  [loader regression](../../../probes/rtabmap/tests/plugin-loader.cpp) uses the
  exact patched private header, a real shared module, symbol lookup and unload.

The [shared profile](features.cmake) disables OBSENSOR explicitly. Native Linux
would otherwise detect its V4L2 backend even with general V4L support disabled.
This is a package feature selection, separate from the source patches.
The canonical recipe patches are the builder authority. Historical probe patch
copies retain their provenance and do not select this package's source changes.

Runtime and memory-analysis results belong in the related
[validation record](../../../probes/rtabmap/VALIDATION.md).
