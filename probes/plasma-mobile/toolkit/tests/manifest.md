# Toolkit source and export checks

The exporter discovers every directory below `recipes/category/package`.
The default contract is a complete package with its own `distinfo` and one source archive.
[sources.tsv](../sources.tsv) records each original archive URL and SHA256.
[source-owners.tsv](../source-owners.tsv) records only exceptions.

The exception fields are recipe, source owner, kind, and primary archive.
Use tabs between fields. Use `-` when the owner's selection is sufficient.

- `package` requires a Makefile and PLIST. A shared consumer must include its owner's `Makefile.common` directly and unconditionally.
- `meta` requires `META_PACKAGE=yes`. It can own shared source metadata without a fake PLIST.
- `overlay` contains only changed files. The exporter preserves the pinned base recipe and copies those files over it.
- Multiple archives require an explicit primary archive. Source patches apply only to that archive. Supplemental dictionaries and test data still require checksums.

A source owner must have one complete `distinfo`. It must list every archive and patch exactly once.
Shared consumers cannot carry local `distinfo` or `patches`, or override `DISTINFO_FILE` and `PATCHDIR` in their make fragments. The same restriction applies to overlay files and their pinned base. This static contract does not evaluate arbitrary bmake expressions. Owners cannot form chains. Shared-source packages must use the canonical owner instead of duplicate archive rows.
The validator rejects missing recipes, source rows, digests, patch files and invalid exceptions before export.
The source check then verifies the actual archives and applies patches with zero fuzz.

Run from the repository root. Each result directory must be new.
The tests need BSD make, tar with zstd support, zip, patch, shasum and OpenSSL with BLAKE2s.
Set `BMAKE` and `OPENSSL` when these tools are outside PATH.

```sh
sh probes/plasma-mobile/toolkit/validate.sh probes/plasma-mobile/toolkit
sh probes/plasma-mobile/toolkit/tests/manifest.sh /absolute/new-manifest-results
sh probes/plasma-mobile/toolkit/tests/selection.sh probes/plasma-mobile/toolkit /absolute/new-selection-results
sh probes/plasma-mobile/toolkit/tests/source-profile.sh /absolute/verified-distfiles /absolute/new-source-results
```

`manifest.sh` uses small real archives. It covers normal packages, shared sources,
metadata-only recipes, partial overlays, `.tar.zst`, `.zip` and multiple archives.
Its auxiliary archive appears first and cannot take the primary source patch.
Negative cases cover incomplete metadata, wrong digests and invalid ownership.
`selection.sh` checks only recipes that use the Qt, Frameworks or Plasma version selectors.
Independent dependencies keep their own versions.

The full source profile also checks every exported recipe, shared version file and provenance manifest.
An overlay check compares its changed files and the unchanged pinned Makefile.
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
It covers the complete recipe layers in the standard exporter: development-toolchain,
common-build-tools, common-graphics, common-media and this toolkit.
Sparse profiles outside that exporter have a separate ownership contract.
This check does not replace archive hashes, patch digests, zero-fuzz application or clean-commit export checks.

The regression creates a private Git fixture with a global `*.build` ignore pattern.
It verifies that an untracked source patch fails the publication check.
The repository's narrow patch exception permits normal `git add` and preserves the patch in a Git archive.
Ordinary build outputs remain ignored. The test does not change the user's Git configuration.
