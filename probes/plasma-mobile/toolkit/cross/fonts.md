# Current desktop fonts and target install hooks

The common desktop uses Noto's `2026.10.01` monthly release and the Noto CJK
`Serif2.003` tag, commit `9b0f1436e455d902de067a2501422e5dc71ad16b`.
The latter provides the current Sans, Mono and Serif variable collections.
They replace FrameworkIntegration's obsolete `noto-ttf-20230927` aggregate,
retaining CJK coverage. Archive URLs, SHA256 and recipe checksums live in
the canonical [Noto](../../../../pkgsrc/fonts/noto-fonts/) and
[Noto CJK](../../../../pkgsrc/fonts/noto-cjk-fonts/) recipes. Upstream licenses are preserved.

Noto's package includes all 2,171 hinted TTF files from that monthly archive;
the CJK package adds three collections. The explicit PLIST is derived from
those archive members, with duplicate basenames rejected. The target package
also installs Noto's font license. Variable/unhinted duplicates from the
monthly repository are not installed, matching the existing hinted TTF profile.

## Cross-build correction

pkgsrc's modular X font hooks previously requested `mkfontscale:run` and
`mkfontdir:run` through the host tool framework, which rejects this cross case.
[The shared font-role delta](../../../../profiles/common-build-tools/cross/font-runtime-roles.md)
makes them explicit target package dependencies and embeds target X11 paths
in both install frameworks. It covers bitmap, TrueType and Type1 fonts.
The native build branch and non-modular font handling stay unchanged.
The target package performs real font indexing during installation.

The full `noto-fonts-20261001`, `noto-cjk-fonts-20240730`, `mkfontscale-1.2.4`,
`libfontenc-1.1.9` and `encodings-1.1.0` packages pass normal package checks.
FrameworkIntegration 6.31 then builds against this common font selection.

## CM5 acceptance

On 2026-10-12, CM5 Rev 1.0 / BCM2712 D0 / 4 GiB / Waveshare CM5-NANO-B passes
[the installed-font check](../tests/fonts-runtime.sh):

```sh
sh fonts-runtime.sh EXPECTED_PAYLOAD_SHA256 NEW_OUTPUT
```

The expected manifest contains the package payload paths under `/usr/pkg`,
with their SHA256 independently compared against the common sysroot.
All 2,234 regular payload files match on CM5. Normal package integrity checks
pass. The real target install hooks produce `fonts.dir` and `fonts.scale`,
both with 5,766 entries; no host paths appear in them. Fontconfig scans Latin
and all three CJK collections, and resolves explicit Russian/Japanese requests
to the expected installed Noto files. The fan kernel and boot time are unchanged.

Result archive SHA256:
`57d541e4b1ee191c9d07f0c5206b1d019d2c973448e62ad22b9cfcc49ce3b3fe`.
This checks installed data, indexing and selection. It does not establish
complete language shaping coverage or acceptance of a Plasma session.
