# Cross font indexer roles

The shared [framework delta](../patches/pkgsrc-font-runtime-roles.patch)
keeps modular X font indexers in target package install hooks. It applies to
`mk/pkginstall` and `mk/pkgtasks` in every common profile. It replaces the
former Plasma-only delta. It covers bitmap, TrueType and Type1 font packages.

Cross font packages declare normal runtime dependencies on
`fonts/mkfontscale>=1.2` and `fonts/encodings`. The mkfontscale package owns
both `mkfontdir` and `mkfontscale`. Hooks use their installed target
`${X11BASE}/bin` paths. They do not embed the native tool prefix or sysroot.
All font data, index hooks and cache-update settings remain enabled.
Native and non-modular branches keep their previous tool selection.

Font compilation still uses native tools. For example, `font-misc-misc`
keeps `bdftopcf`, `ucs2any` and `gzip`; `font-cursor-misc` keeps `bdftopcf`
and `gzip`. Runtime indexing does not require a native mkfontscale package.
A recipe that invokes an indexer while building must declare its native
build tool separately. The general cross `USE_TOOLS+=mkfontdir:run` rejection
remains active.

The [source regression](../tests/font-runtime-roles.py) uses Python 3.15 and
the explicit SDK API 1. It copies the real framework and four actual recipes
to private views. The source view supplied by `--pkgsrc` is read only.

```sh
python3.15 -B profiles/common-build-tools/tests/font-runtime-roles.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --pkgsrc /absolute/prepared-pkgsrc \
    --native-makeconf /absolute/native.mk.conf \
    --cross-makeconf /absolute/cross.mk.conf \
    --bmake /absolute/native/bin/bmake --work /absolute/new/check
```

The regression verifies original source hashes and applies the shared delta
with zero fuzz. Its 32 metadata cases cover both frameworks, native/cross
roles and before/after states for `font-misc-misc`, `font-cursor-misc`,
`dejavu-ttf` and `font-adobe-utopia-type1`. The original cross branches
reproduce the run-tool rejection. Repaired branches declare target runtime
dependencies and exact hook paths. Native dependency lists and actual native
font-generator paths remain unchanged. Two explicit run-tool controls still
fail the cross policy. The runtime font-hook template and tool policy remain
byte-identical. Logs and input hashes are stored in the new work directory.

This is source and metadata acceptance. It does not compile font data,
build packages, execute target hooks or establish X11 display behavior.
Use normal GCC16 package builds and installed target font/cache checks for
those gates. The existing [Plasma font checks](../../../probes/plasma-mobile/toolkit/cross/fonts.md)
retain their separate runtime evidence.
