# Common V8 source

`lang/v8` owns the upstream revision and the combined Ports patch set. Its
source-only package provides the tree, headers and tools; it does not provide
a V8 library. Node and Chromium-based consumers build their own ABI-specific
artifacts from this source.

The producer prepares the effective exported recipe with the selected SDK
source-preparation API, checks the archive hashes and version header, applies
the complete patch inventory, and records an identity for the resulting tree.
The output directory must not exist.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/v8/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/v8-15.6.75.31-5467f0a017e04ff016021a01687868c90af198e5.tar.gz" \
  --patch "$HOST_PREFIX/bin/gpatch" --output "$WORK/v8-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/v8/source.py \
  --sdk-source "$SDK_SOURCE" verify-source --source "$WORK/v8-source" \
  --pkgsrc-root "$PKGSRC_EXPORT"
```

Preparation does not establish that a consumer builds, links or runs. In
particular, GN actions must use the selected Python interpreter and NetBSD host
snapshot generation needs an explicitly selected PaX utility.

`verify-source` compares the receipt with the effective recipe in the selected
prepared pkgsrc export; the export producer is responsible for its freshness.
`verify-payload --source` checks only the prepared tree and receipt, without
claiming compatibility with a particular export.
