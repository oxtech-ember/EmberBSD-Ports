# Shared libarchive 3.8.10 sources

Common profiles update the existing pkgsrc vendor owner at
`archivers/libarchive/files`. They retain its extraction rules and bootstrap
behavior. `archivers/libarchive`, `archivers/bsdtar`, and the bundled route in
`pkgtools/pkg_install` use this one source tree. `archivers/pixz` keeps its
ordinary libarchive package dependency. The bsdtar common-zlib delta remains
in place. `pkg_install` advances to revision 4 because its static payload changes.

## Source origin

Libarchive [3.8.10](https://github.com/libarchive/libarchive/releases/tag/v3.8.10)
was released on 2026-10-14. It adds 7z filters and the tar `--mode` option,
and contains security and bug repairs. The original release archive and its
SHA256 are recorded in [sources.tsv](../sources.tsv).

The export applies these unmodified NetBSD patches in order:

1. [f09692cc](https://github.com/NetBSD/pkgsrc/commit/f09692cc2727cf2defd37e5331aab77679b5d1e7)
   imports new files and updates files without local pkgsrc changes.
2. [fa7406b5](https://github.com/NetBSD/pkgsrc/commit/fa7406b5b9db17afe08b0ab675ee45f3121b365e)
   merges the remaining vendor update and selects version 3.8.10.
3. [318cf450](https://github.com/NetBSD/pkgsrc/commit/318cf4509f47ad80519d1905ac7673a3c516bb31)
   replaces `$^` in test-list generation for older supported bmake versions.

All three patches retain original authorship and licenses. Their byte hashes
are pinned in [sources.tsv](../sources.tsv) and checked before application. Git applies the
original binary manual updates as well as source and regression data.
`pkgsrc-libarchive-consumers.patch` carries the same bmake correction into
`Makefile.in`, which is used with `--disable-maintainer-mode`, and bumps the
pkg_install revision. This small companion is an AI-assisted EmberBSD adaptation.

## Checks and remaining acceptance

Run the source regression against an unchanged 3.8.9 pkgsrc export:

```sh
python3 profiles/common-build-tools/tests/libarchive-source.py \
  --pkgsrc /absolute/baseline-pkgsrc \
  --archive /absolute/distfiles/libarchive-3.8.10.tar.xz \
  --bmake /absolute/bmake --work /absolute/new-work
```

The regression checks every Git postimage in the original patches. It checks
that the official release's source and test payload remains present. It runs
the actual five test-list recipes with bmake and independent expected output.
It records whether the selected bmake exposes the original `$^` defect.
[the metadata check](../tests/bsdtar-common-zlib.py) checks native and cross dependency routing on a
complete exported tree with qualified make configurations.

The source check passes 480 Git postimages, presence of 1,135 upstream test
and data files, and five real bmake test-list generators. The selected bmake
already supports `$^`; this run does not reproduce the older-bmake failure.
All five native/cross metadata variants pass with the Python check.

These checks do not compile libarchive or run its upstream executable tests.
Native and target packages, upstream `check`, static analysis, memory checks,
installed bsdtar/pixz consumers, and package lifecycle acceptance remain separate.
The package tools' built-in-system-library route uses the selected system
library; updating the vendored tree alone does not update that system library.
A planner must hash the copied `FILESDIR.libarchive` input for bsdtar and
pkg_install. Their source-copy route does not create a dependency on the
installed libarchive package.
