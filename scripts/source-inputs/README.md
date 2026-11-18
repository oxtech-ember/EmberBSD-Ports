# Shared source producers

Each `NAME/source.py` prepares one common source for the OS and for Ports. All
producers have the same interface, so a build plan runs them the same way:

```sh
python3 -B scripts/source-inputs/NAME/source.py --sdk-source SDK --git GIT \
  prepare --distdir DISTFILES --patch GPATCH --output NEW_DIRECTORY \
  [--pkgsrc-export EXPORT --export-patch GPATCH]
```

`--distdir` is the directory with the distfiles of the effective recipe; the
producer selects its archives by the recipe (`scripts/source_distdir.py`) and
names a missing one. `--archive` selects one archive
explicitly instead. Other tools come from the prefix of `--patch` (rcs
finds `lzip` there). A recipe without a distfile (libarchive, libfetch) takes no
`--distdir`. `--pkgsrc-export` reuses one shared export from
`scripts/pkgsrc-shared-export.py` instead of a private export for each source.

`scripts/prepared-source-current.py --describe NAME` prints the effective recipe
identity and the distfiles of the effective distinfo without an export. A
build plan uses the identity as the input of the source, and the distfile list
to know whether the producer needs `--distdir`. The list can also name a
distfile that the recipe does not fetch.

AutoGen libopts needs `--pkgsrc-export`: its generation reads the shared export.
