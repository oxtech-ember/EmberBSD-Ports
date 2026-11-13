# Common V8 source

`lang/v8` owns the upstream revision and the combined Ports patch set. Its
source-only package provides the tree, headers and tools; it does not provide
a V8 library. Node and Chromium-based consumers build their own ABI-specific
artifacts from this source.

Electron 45.3.2's complete ordered V8 series is pinned to Electron commit
`9ee9e7718172287d068cee397097c2d79a137eec`. The numbered patches preserve its
order and attribution; the separate prepared-source identity patch retains
EmberBSD's receipt-bound code-cache salt. Verify the series against the pinned
Git object using `test-electron-series.py --git /path/to/git --electron-source
/path/to/electron`. Other consumers use the same effective V8 tree.

The producer prepares the effective exported recipe with the selected SDK
source-preparation API, checks the archive hashes and version header, applies
the complete patch inventory, and records an identity for the resulting tree.
The packaged tree records the effective recipe and the exported producer hash;
verification checks both against the selected recipe and current producer.
The output directory must not exist.

`prepare --previous-source /absolute/previous-v8` optionally preserves mtimes
of unchanged files from an already prepared V8 tree, including across recipe
versions, using an SDK with `PREPARED_TREE_REUSE_API=1`. The new output is a
separate tree and the previous source remains read-only. The caller must hold
the appropriate workspace locks and drain writers before reuse.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/v8/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/v8-15.6.75.57-5e51e9c6079c7fa65ca75e7919c81ea50734302e.tar.gz" \
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
