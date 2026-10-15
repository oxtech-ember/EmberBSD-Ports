# OMPL source provenance

[OMPL 2.0.2](https://github.com/ompl/ompl/releases/tag/2.0.2) was released on
2026-08-14 and remained current stable on 2026-10-15. Its tag names commit
`1ae6ac0bf7e9cb67d8994a8b8742833f813fdd39`. [sources.tsv](sources.tsv)
pins the complete official release asset, including upstream submodules.
SHA256: `b9155e243e555b04b01f8e4ff7e21a48582edbab9c300a611289655778bcd29d`.
OMPL retains Rice University/contributor authorship and BSD-3-Clause terms.
VAMP and nanobind sources remain intact but are excluded from this profile.

[Common dependencies](cross/sources.tsv) are Eigen 5.0.1 and Boost 1.92.0.
Eigen preserves MPL-2.0 and its other shipped license notices. Boost preserves
the Boost Software License 1.0. Package source receipts and licenses install
under `share/licenses/{eigen3,boost-headers,boost-libs}`.
Boost supplies full headers and the selected serialization/program_options/test
compiled closure. Other prepared Boost 1.91 consumers are not claimed migrated.
No private or legacy dependency copy is used.

The AI-assisted EmberBSD [metadata patch](../../pkgsrc/local-robotics/ompl/patches/patch-pkgconfig)
fixes pkg-config dependency names, versioned headers and public Boost/thread
flags. A real archive-template consumer demonstrates the missing-public-Boost
link failure. The patch preserves upstream fallback behavior for optional or
static configurations, which are outside this acceptance. No upstream C++
source patch is needed. The patch is not submitted or accepted upstream.
`distinfo` records its pkgsrc-normalized SHA1.

The original EmberBSD geometry oracle now expands rectangle faces by a small
roundoff guard. A decimal corner tangent reproduces the old missed collision.
Direct fixtures and integer-orientation comparisons verify the correction.
This is a fix to our oracle, not an OMPL source modification.

The selected C++ build and tests require no Python. Upstream demo sources and
`ompl_benchmark_statistics.py` retain their original labels and require
Python only when invoked. New recipes, examples and tests disclose AI
assistance; individual SPDX notices specify MIT or BSD-2-Clause terms.
[Validation](VALIDATION.md) records acceptance and analysis limits.
