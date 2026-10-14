# Ruckig provenance

Ruckig [v0.19.4](https://github.com/pantor/ruckig/releases/tag/v0.19.4),
released 2026-07-15, was the latest stable release checked on 2026-10-14.
Its tag resolves to `a8db97a4e9c55e5160a3855f739fa3b270df8e4c`.
The archive URL and SHA256 are pinned in [sources.tsv](sources.tsv).

Upstream is MIT licensed, copyright 2021 Lars Berscheid. Its complete notice
is installed as `share/ember-ruckig/licenses/Ruckig-MIT`. No source or algorithm
patch is applied. Cloud client, examples, benchmarks and Python bindings are
disabled through upstream options. The C++20 shared library retains its
upstream package export; this profile does not promise a stable ABI across
different Ruckig releases.

The recipes and independent C++ contracts are original MIT-licensed EmberBSD
work developed with AI assistance. Builder structure follows the existing
Fusion profile. No changes have been sent to or accepted by upstream.
Fixtures use analytic jerk-limited motion and original synthetic inputs.

The GCC16 pkgsrc recipe and cross helper install the complete shared-library
development interface. Their feature cache preserves the existing local
algorithm profile and enables upstream tests. The
[AArch64 target receipt](cross-validation.md) records real installation,
numerical checks, removal/reinstallation and source-analysis limitations.
