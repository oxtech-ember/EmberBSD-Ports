# Toolkit source and export checks

The toolkit recipes are canonical recipes in `pkgsrc/category/package`.
The two manifests select them: every recipe in a manifest row is a toolkit recipe.
The validator reads them from `pkgsrc/`, or from an optional second argument.
A recipe that includes a toolkit version selector or a shared source owner must have a row.
The default contract is a complete package with its own `distinfo` and one source archive.
[sources.tsv](../sources.tsv) records each original archive URL and SHA256.
[source-owners.tsv](../source-owners.tsv) records only exceptions.

The exception fields are recipe, source owner, kind, and primary archive.
Use tabs between fields. Use `-` when the owner's selection is sufficient.

- `package` requires a Makefile and PLIST. A shared consumer must include its owner's `Makefile.common` directly and unconditionally.
- `meta` requires `META_PACKAGE=yes`. It can own shared source metadata without a fake PLIST.
- `local` is limited to the explicit self-owned `sysutils/ember-plasma-session` recipe. It has empty `DISTFILES`, `NO_BUILD=yes` and no archive metadata. Its `files/` directory holds only the two canonical service files, as regular files. It does not exempt upstream recipes from source checks.
- Multiple archives require an explicit primary archive. Source patches apply only to that archive. Supplemental dictionaries and test data still require checksums.

A source owner must have one complete `distinfo`. It must list every archive and patch exactly once.
Shared consumers cannot carry local `distinfo` or `patches`, or override `DISTINFO_FILE` and `PATCHDIR` in their make fragments. This static contract does not evaluate arbitrary bmake expressions. Owners cannot form chains. Shared-source packages must use the canonical owner instead of duplicate archive rows.
The validator rejects missing recipes, source rows, digests, patch files and invalid exceptions before export.
The source check then verifies the actual archives and applies patches with zero fuzz.

Registry crate archives are ordinary auxiliary inputs. The CSS parser owner selects
its exact registry closure from the patched Cargo.lock and records each original
crates.io archive and SHA-256 in the source manifest.

Run from the repository root. Each result directory must be new.
The tests need BSD make, tar with zstd support, Python, patch, shasum and OpenSSL with BLAKE2s.
Set `BMAKE`, `OPENSSL`, `PYTHON`, `TAR` and `SH` to selected tools when needed.

```sh
sh probes/plasma-mobile/toolkit/validate.sh probes/plasma-mobile/toolkit
sh probes/plasma-mobile/toolkit/tests/manifest.sh /absolute/new-manifest-results
python3 probes/plasma-mobile/toolkit/tests/cssparser-crates.py --archive /absolute/distfiles/cxx-rust-cssparser-1.1.0.tar.gz --patch-tool /absolute/host/bin/gpatch
sh probes/plasma-mobile/toolkit/tests/selection.sh probes/plasma-mobile/toolkit /absolute/new-selection-results
sh probes/plasma-mobile/toolkit/tests/source-profile.sh /absolute/verified-distfiles /absolute/new-source-results
```

`manifest.sh` uses small real archives. It covers normal packages, shared sources,
metadata-only recipes, `.tar.zst`, `.zip` and multiple archives.
Its auxiliary archive appears first and cannot take the primary source patch.
Negative cases cover incomplete metadata, wrong digests and invalid ownership.
`cssparser-crates.py` compares every registry archive identity and checksum in
the toolkit source plan against the actual upstream lock after its Ports patch.

These checks do not establish package builds, target execution or desktop acceptance.
They preserve the recorded recipe versions and do not claim that every provider is the newest release.

## Publication inputs

Before publication, stage the complete recipe changes and run these checks from the repository root:

```sh
sh scripts/check-published-patches.sh
sh scripts/tests/published-patches.sh /absolute/new-publication-results
```

The publication check reads tracked `distinfo` files from the working tree.
Every declared patch must exist and appear in the Git index.
It covers the complete recipe layers in the export: `pkgsrc/`,
common-build-tools and common-graphics. The toolkit recipes are in `pkgsrc/`.
Sparse profiles outside the export have a separate ownership contract.
This check does not replace archive hashes, patch digests or zero-fuzz application.

The regression creates a private Git fixture with global `*.build` and `Makefile` ignore patterns.
It verifies that an untracked source patch fails the publication check.
The repository's narrow patch exception permits normal `git add` and preserves the patch in a Git archive.
Ordinary build outputs remain ignored. The test does not change the user's Git configuration.
The firmware selection check exports the complete common-media profile with
canonical gmake/dtc providers and GCC16. Invalid flags and incomplete firmware
opt-ins must fail before creating the destination.

The normal export contains the 160 toolkit recipes and the complete
`meta-pkgs/kde` and `meta-pkgs/qt6` selectors from `pkgsrc/`. Boost headers,
Boost libraries, Phonon and Kirigami Addons use the identical pinned upstream
recipes. Compared with the former profile export, only the common iso-codes,
Hunspell, US English dictionary, NSS and ebook-tools recipes differ. They come
from upstream with the common patches. The manifest regression includes 41 rejected variants.
These are source/export checks; they do not rebuild every package or establish
a working desktop.
