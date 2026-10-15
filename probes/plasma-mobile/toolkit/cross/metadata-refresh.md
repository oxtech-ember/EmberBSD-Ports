# Refresh metadata for an unchanged package payload

A `MAKE_DIRS` or configuration-script repair does not change compiled code.
Do not rebuild C++ solely to regenerate those package records.
Use the normal pkgsrc metadata and archive generators with an accepted staging tree.
Keep the original compilation receipt and identify the later packaging revision separately.

## Preconditions

The source archive, source patches, compiler, options, target ABI and payload must match the accepted build.
Check the effective PLIST and all payload hashes, including symbolic link targets.
Record SHA256 for every staged ELF file before and after the refresh.
Use the existing native pkgtools, build configuration and private metadata database.
Keep the original archive unchanged and use a new output directory.

This procedure requires the accepted `DESTDIR`, generated PLIST and dependency records.
The build's tools and make inputs must still be readable.
It does not require a new compile, configure or stage-install phase.
It does not verify reconstruction of a removed build state from an archive alone.

Unchanged dependency constraints may reuse the accepted resolved dependency records.
Changed constraints require fresh resolution and a separate ABI compatibility check.
Do not copy an old `.rdepends` into a package with new runtime requirements.
Do not describe refreshed metadata as a fresh compilation against a different library.

## Generate new records

Set `BMAKE`, `recipe`, `makeconf`, `workobj` and `pkgdb` from the accepted build receipt.
Retain its target settings and native tools. Set `refresh` to a new absolute directory.

```sh
pkgmake()
{
    "$BMAKE" -C "$recipe" "MAKECONF=$makeconf" \
        "WRKOBJDIR=$workobj" "_PKG_DBDIR=$pkgdb" "$@"
}

name=$(pkgmake -V '${PKGNAME}')
mkdir "$refresh"

refresh_make()
{
    pkgmake "PKG_DB_TMPDIR=$refresh/pkgdb" \
        "_PKGINSTALL_DIR=$refresh/pkginstall" \
        "_DEPENDS_PLIST=$refresh/PLIST_deps" \
        "STAGE_PKGFILE=$refresh/$name.tgz" \
        "PKGFILE=$refresh/$name.tgz" "$@"
}

refresh_make generate-install-scripts
refresh_make _pkgformat-generate-metadata
refresh_make package-create
```

These are the real pkgsrc backends, including `pkg_create` and its PLIST checks.
The example uses private make targets and variables. Check them against the pinned pkgsrc revision before reuse.
The tested baseline is `fff4deb639a1a640476203c80f752fb77b6cb14b`, with the common EmberBSD cross-package patches.
The old install metadata and script cache are not reused.
Do not create compile or install completion cookies to bypass a phase.

The public `repackage` target is different: its `_package-clean` removes `DESTDIR`.
It then repeats stage-install from the retained build. It is not the narrow refresh above.

## Verify the result

Run the [package payload and metadata auditor](../tests/package-set.md).
Compare every payload member with the accepted archive; permit only the intended metadata changes.
Check target paths in every generated script, including `SORT`, and reject host wrapper paths.
Run the changed script's actual lifecycle, such as the [Workspace configuration test](../tests/workspace-config.md).
Recheck runtime closure when dependency metadata changes.
Retain both archive hashes, the source revisions, exact commands and original compilation evidence.

In the Workspace 6.8.0nb2 macOS check, the three backend commands take about 29 seconds.
All 6,101 staged entries remain unchanged, including 149 ELF objects.
Both archives pass payload and metadata audits; their payload manifests match exactly.
The generated configuration helpers pass install, remove, reinstall and edited-menu preservation.
These measurements cover packaging on macOS. They do not establish target installation or a working Plasma session.
