# Common gzip 1.15

Origin: pkgsrc, maintained by EmberBSD (AI-assisted).

The recorded pkgsrc import updates the inherited `archivers/gzip` recipe in every export.
It keeps all fourteen commands, manual pages, Info documentation and conflicts.
The existing `LESS=less` export patch keeps zless as a runtime pager frontend.
It does not require less on the build host. No second recipe is maintained.

GNU published the stable release on 2026-09-20.
The [announcement](https://lists.gnu.org/archive/html/info-gnu/2026-09/msg00006.html)
binds tag `v1.15` to commit `e6263160768c73f6117f3c1de78291a60f2cb796`.
The license remains GPL-3.0-or-later. Upstream copyright notices remain intact.

The official [source archive](https://ftp.gnu.org/gnu/gzip/gzip-1.15.tar.xz)
has 808900 bytes and SHA256
`9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48`.
This hash matches the announcement's Base64 checksum.
Its uncompressed tar has 5396480 bytes and SHA256
`db2d827bc811f348a11da04484bd2c5971ff729a83c5d9f7a3ad6df206b94e92`.
The recipe retains the pkgsrc uncompressed mirror archive for bootstrap use.
`distinfo` also binds its BLAKE2s and SHA512 hashes.
These agree with the [pkgsrc update](https://mail-index.netbsd.org/pkgsrc-changes/2026/09/24/msg355273.html).
The detached GNU signature is available. Signature authentication remains a separate check.

Both inherited source patches are already in upstream 1.15.
`lib/utimens.h` includes `sys/stat.h` for the NetBSD declarations.
`unlzh.c` clears the shared decoding tables before reuse.
No source patch is applied a second time. The complete upstream source is retained.
The release also binds output cleanup to its directory descriptor.
This repairs the reported wrong-file deletion during an ancestor rename.
The source check does not reproduce that race or malformed-input defects.

The common pkgsrc gzip, gunzip and gzcat tool routes keep this provider.
Rust and compiler-cache integration also name `archivers/gzip`.
The LXQt archiver's `gzip>=1.14` constraint accepts 1.15 without another recipe.
Rebuild selected tool consumers from a fresh dependency graph.

Run the source check with an explicit SDK Python:

```sh
/absolute/sdk/python3.15 -B profiles/common-build-tools/tests/gzip-source.py \
  --archive /absolute/distfiles/gzip-1.15.tar.xz \
  --tar /absolute/distfiles/gzip-1.15.tar --pkgsrc /absolute/export -v
```

Native metadata additionally requires `--metadata-selection /absolute/selection.json`.
Its object has exactly `make`, `work`, `environment` and `record`.
`make` is the complete SDK tuple: selected bmake, `-m`, owned mk root,
`SHELL=/selected/mksh` and `MAKECONF=/private/work/mk.conf`.
All paths are explicit and absolute. The makeconf, home, temporary and cache paths
stay inside `work`. It must select private `pkgdb`, `objects` and `prefix` directories.
The environment contains only `HOME`, `TMPDIR`, all three `XDG_*_HOME` paths,
`PATH`, `LC_ALL=C`, `TZ=UTC` and the same `MAKECONF`.
It does not inherit `MAKEFLAGS`, shell startup inputs or other ambient variables.
The new `record` file stays inside the prepared export and retains exact argv and environment.
The fixture checks `.SHELL`, `.SYSPATH`, `!=` and `:sh` with the selected mksh.
Parse-time warnings fail even when make returns zero.
Supply existing pkgsrc cached host facts explicitly to avoid automatic tool discovery.
Run `profiles/common-build-tools/tests/test_gzip_metadata.py` for refusal controls.
This fixture does not qualify its configure command tools or an ordinary SDK provider.

Source hashes, retired-patch content and export composition are separate from execution.
Native GCC16 compilation, upstream tests, package lifecycle and consumer runtime remain pending.
Cppcheck, applicable path analysis and memory checks also remain pending.
Ordinary round trips should cover empty, text and binary input, stdin and named files.
Check `gzip -t`, decompression byte equality, helpers and retained source files.
Use independent input bytes and `LC_ALL=C` for deterministic diagnostics.
The release now respects the locale for number formatting and filename quoting.
Its `gzip -l` empty-file ratio and znew `-P` warning also change as documented upstream.

## Failing decompressor

The pkgsrc extract script pipes `GZCAT`, `BZCAT`, `XZCAT` and the other
decompressors into tar, cpio or the shell. A pipeline returns the status of
its last command. Without its decompressor, an archive extracted nothing and
`extract` still returned 0. A corrupt gzip trailer also passed: gzip writes
the data, reports the CRC error and exits 1, but tar returns 0.

The common export checks an absolute decompressor path first and fails with
`extract: decompressor not found: PATH`. Relative upstream defaults such as
`gzip -cd` are unchanged. Each pipeline then records a failing decompressor
status in a file under `TMPDIR`, without `pipefail`, so `/bin/sh` and mksh
behave the same. After the archive program, `extract` fails with
`extract: decompressor failed with status N: DISTFILE`. Status 141 or 269 is
SIGPIPE: tar may stop at the end-of-archive blocks before the decompressor
has written its zero padding, so that status is ignored.

Run this check from the repository root:

```sh
PATCH=/absolute/patch GZIP=/absolute/gzip TAR=/absolute/tar \
    EXTRACT_SH=/absolute/sh sh profiles/common-build-tools/tests/extract-decompressor.sh \
    /absolute/unpatched-pkgsrc /absolute/new-results
```

The regression uses the real pkgsrc script. The unpatched script must give
silent success for missing, corrupt and relative missing decompressors. The
patched script refuses missing, non-executable, shar and bzip2
decompressors, a corrupt gzip with and without excludes and a missing relative
decompressor. It still extracts with an absolute or a relative gzip and with
a padded archive that ends tar early.
