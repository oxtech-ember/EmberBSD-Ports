# Common gettext source

Prepare and verify the complete shared `devel/gettext` archive and patch set.
The `devel/gettext-tools` recipe uses the same `Makefile.common`, distinfo and
patches; its build and dependency options remain consumer policy. The source
contains GNU gettext tools and runtime: the native OS consumer retains its
separate Citrus libintl implementation.

The optional `EMBER_GETTEXT_PLAIN_STYLE=yes` configure environment selects the
upstream plain-output stream implementation for base tools. It does not build
libtextstyle, preserves ordinary catalog output, and rejects the newer color and
CSS options. The default package mode retains full styling support.
The plain-output profile requires an external libxml2 and rejects configure's
otherwise automatic bundled XML fallback. Its consumer selects the common
target library and headers.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/gettext/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/gettext-1.0.tar.gz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/gettext-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/gettext/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/gettext-source" --archive "$DISTFILES/gettext-1.0.tar.gz" \
  --patch "$HOST_PREFIX/bin/gpatch"
```

The archive includes upstream licenses and notices. If effective source inputs
change, verification prepares and compares the complete payload.

`profiles/common-build-tools/patches/gettext-reloc-wrapper-access.patch`
is exported as `devel/gettext/patches/patch-zz_ember_reloc_wrapper_access`.
Both `progreloc.c` copies call the system `access` while
`install-reloc` builds the wrapper. The archive checksum is unchanged.
Shared `gettext-tools` is `gettext-tools-1.0nb10`; the Darwin native
assignment stays `gettext-tools-1.0nb9`. After this patch lands, refresh a
prepared tree with `refresh-source` so its receipt names the new patch set.

The common gettext-tools build links the shared `textproc/tree-sitter`
runtime, while its language grammars remain pinned in `tree-sitter.cfg`.
Prepare that runtime with the dedicated [Tree-sitter source owner](../tree-sitter/README.md)
and make its target `tree-sitter.pc`, headers, and library available through
the selected target `pkg-config`. The configure probe checks the compatible
grammar ABI and linkable runtime before building gettext scanner backends.

For unchanged prepared payloads, `refresh-source --source "$OUTPUT" --archive
"$ARCHIVE" --patch "$PATCH"` verifies the payload and current source identity,
then atomically updates its receipt to the current scoped identity. Supply
`--pkgsrc-export` when using a shared export. The caller must hold exclusive
use of the prepared source throughout verification and refresh; this command
does not acquire that lock. A failed verification leaves the receipt unchanged.
