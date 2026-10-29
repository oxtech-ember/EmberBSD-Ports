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
  --scoped-identity --output "$WORK/gettext-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/gettext/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/gettext-source" --archive "$DISTFILES/gettext-1.0.tar.gz" \
  --patch "$HOST_PREFIX/bin/gpatch"
```

The archive includes upstream licenses and notices. If effective source inputs
change, verification prepares and compares the complete payload.
