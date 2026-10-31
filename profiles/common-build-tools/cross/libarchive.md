# Shared libarchive 3.8.11 sources

Common profiles update the existing pkgsrc vendor owner at
`archivers/libarchive/files`. They retain its extraction rules and bootstrap
behavior. `archivers/libarchive`, `archivers/bsdtar`, and the bundled route in
`pkgtools/pkg_install` use this one source tree. `archivers/pixz` keeps its
ordinary libarchive package dependency. The bsdtar common-zlib delta remains
in place. `pkg_install` advances to revision 20 because its static payload changes.

## Source origin

Libarchive [3.8.10](https://github.com/libarchive/libarchive/releases/tag/v3.8.10)
was released on 2026-10-14. It adds 7z filters and the tar `--mode` option,
and contains security and bug repairs. The original release archive and its
SHA256 are recorded in [sources.tsv](../sources.tsv).

Libarchive [3.8.11](https://github.com/libarchive/libarchive/releases/tag/v3.8.11)
was released on 2026-10-30 as a security and bug-fix release. Its archive and
SHA256 are also recorded in [sources.tsv](../sources.tsv).

The export applies these unmodified NetBSD patches in order:

1. [f09692cc](https://github.com/NetBSD/pkgsrc/commit/f09692cc2727cf2defd37e5331aab77679b5d1e7)
   imports new files and updates files without local pkgsrc changes.
2. [fa7406b5](https://github.com/NetBSD/pkgsrc/commit/fa7406b5b9db17afe08b0ab675ee45f3121b365e)
   merges the remaining vendor update and selects version 3.8.10.
3. [318cf450](https://github.com/NetBSD/pkgsrc/commit/318cf4509f47ad80519d1905ac7673a3c516bb31)
   replaces `$^` in test-list generation for older supported bmake versions.

4. `pkgsrc-libarchive-3.8.11.patch` applies the official 3.8.10 to 3.8.11
   release difference to `archivers/libarchive/files`, takes `configure`
   verbatim from 3.8.11, and selects version 3.8.11. It is an AI-assisted
   EmberBSD adaptation generated from the two official release archives.

The NetBSD patches retain original authorship and licenses. All four byte hashes
are pinned in [sources.tsv](../sources.tsv) and checked before application. Git applies the
original binary manual updates as well as source and regression data.
`pkgsrc-libarchive-consumers.patch` carries the same bmake correction into
`Makefile.in`, which is used with `--disable-maintainer-mode`, and bumps the
pkg_install revision. This small companion is an AI-assisted EmberBSD adaptation.
At the end of the export, `pkgsrc-libarchive-3.8.11-revisions.patch` drops the
libarchive and bsdtar revisions for the new version and moves pkg_install to
revision 20, past the published revision 19.

## Checks and remaining acceptance

Run the source regression against an unchanged 3.8.9 pkgsrc export:

```sh
python3 profiles/common-build-tools/tests/libarchive-source.py \
  --pkgsrc /absolute/baseline-pkgsrc \
  --archive /absolute/distfiles/libarchive-3.8.11.tar.xz \
  --bmake /absolute/bmake --work /absolute/new-work
```

The regression checks every Git postimage in the original patches. It checks
that the official release's source and test payload remains present. It runs
the actual five test-list recipes with bmake and independent expected output.
It records whether the selected bmake exposes the original `$^` defect.
[the metadata check](../tests/bsdtar-common-zlib.py) checks native and cross dependency routing on a
complete exported tree with qualified make configurations.

The source check passes 678 Git postimages, presence of 1,160 upstream test
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

## Security warning interpretation

The selected 3.8.11 source fixes stack exhaustion from unbounded recursion
when reading a malformed ISO9660 Joliet name
([PR 3736](https://github.com/libarchive/libarchive/pull/3736)). It also
contains the uu filter fix
([PR 3693](https://github.com/libarchive/libarchive/pull/3693)) that replaces
the former local `pkgsrc-libarchive-uu-ascii-lines.patch`;
[the uu regression](../tests/libarchive-uu-tar-member.sh) still applies.

It retains these fixes from 3.8.10:

- CVE-2025-60753: the zero-length substitution repair in
  [PR 2787](https://github.com/libarchive/libarchive/pull/2787), including its
  subsequent end-of-string correction in [PR 2809](https://github.com/libarchive/libarchive/pull/2809).
- CVE-2026-4424: the RAR LZSS allocation and bounds checks in
  [d379dc0](https://github.com/libarchive/libarchive/commit/d379dc0b2976b7207d1ad78f5ed3eb99a5b6d375).
- CVE-2026-4426: the zisofs block-size exponent validation in
  [c3cb1c5](https://github.com/libarchive/libarchive/commit/c3cb1c568ebf9e8f7f478cfc0356ae54e99712b0).

The inspected `pkg-vulnerabilities` entries match `libarchive-[0-9]*`;
that wildcard does not specify a fixed-version boundary. The three affected
C files in the export and completed bsdtar build match the official 3.8.10
release byte for byte. The audit database remains unchanged.

The installed macOS arm64 `bsdtar-3.8.10nb2` matches its published package
payload. Its `^` and `a*` global substitutions terminate, and the upstream
`test_option_s` zero-length case produces the exact expected pathname.
The native regex implementation rejects an empty pattern. Listing the
[upstream zisofs regression image](https://github.com/libarchive/libarchive/commit/a2a73a8f14b3208c7f6acbbc93265254a7c1efd0)
reports the small raw entry size, 2064 bytes, with the invalid exponent rejected.
These are installed bsdtar checks, not a run of the complete upstream suite.
The RAR repair PR adds no dedicated regression fixture; its three code checks
are present, but a causal RAR runtime test and instrumented execution remain unverified.
