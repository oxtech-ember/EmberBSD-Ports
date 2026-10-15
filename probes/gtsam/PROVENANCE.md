# GTSAM source and package provenance

The stable [GTSAM 4.3.0 release](https://github.com/borglab/gtsam/releases/tag/4.3.0)
was checked against official upstream on 2026-10-15. GitHub records publication
on 2026-09-18 UTC. This is the final release, not the earlier alpha.
Annotated tag `97b7a5e3b8edce204320397f00b502f57952fb38` resolves to
commit `71a25ca36c084cbad1f872e812d6d97fbadfdb05`.

[sources.tsv](sources.tsv) pins the original codeload archive:
45,746,023 bytes, SHA256
`fa79b78a2cdd2561d4f93b75a61294a39c4d3a2d2e6e70dc51f91e6253966f96`.
The pkgsrc recipe also records upstream BLAKE2s/SHA512 checksums.
No third-party binary package or modified source distribution is substituted.

GTSAM is BSD-3-Clause, copyright Georgia Tech Research Corporation and individual
contributors. The package retains `LICENSE`, `LICENSE.BSD`, source receipts
and the following upstream vendor notices under `share/licenses/gtsam`.
No GTSAM source file is patched; the packaging profile configures upstream's
libm cache and additional-library interface for portable POSIX linkage.

| Component | Selection and license |
| --- | --- |
| Eigen 5.0.1 | Existing common external package; MPL-2.0 and per-file notices. Bundled Eigen headers are unused and not installed |
| CCOLAMD 2.9.6 | Private upstream copy, Tim Davis, BSD-3-Clause, `Doc/License.txt` |
| SuiteSparse_config | Private CCOLAMD companion; its README states no licensing restrictions |
| Spectra 1.1.0 | Private upstream headers, Yixuan Qiu, MPL-2.0; version from `Util/Version.h` |
| Cephes | Upstream copy: MIT top-level license, Stephen L. Moshier attribution, BSL-1.0 notices for John Maddock-derived code and SciPy changes |

These vendors come from the selected current GTSAM release. CCOLAMD uses
GTSAM's private namespace/hidden implementation. They do not create parallel
public provider packages. Spectra/Cephes representative source notices are
retained with license texts; the pinned original archive preserves all notices.
The bundled METIS and Eigen implementation are not installed.

The cross helpers, recipe, numerical contracts and independent example were
written for EmberBSD with AI assistance and are MIT licensed; see [LICENSE](LICENSE).
No upstream acceptance is claimed. The previous 2026-10-07 GCC12 native attempt
was interrupted with exit 130, not a compiler failure. Current GCC16 acceptance
supersedes that incomplete attempt; [validation](VALIDATION.md) distinguishes
native memory checks from actual AArch64 execution.
