# Common ML sources

This producer prepares one explicitly selected source-only Ports owner: `devel/ruy`, `devel/pthreadpool`, `devel/gemmlowp`, `devel/farmhash`, `devel/ml-dtypes`, `devel/neon2sse`, `devel/fxdiv`, or `devel/fft2d`. Versions, archive URLs, checksums and patches belong to each recipe; this frontend selects no versions and downloads nothing. SDK `archive_metadata` API 1 verifies the archive metadata and complete patch inventory; the existing shared source helper and SDK sourceprep extract and apply them.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ml-sources/source.py \
  --package devel/ruy --sdk-source "$SDK_SOURCE" --git /usr/bin/git prepare \
  --archive /absolute/recipe-distfile --patch "$HOST_PREFIX/bin/gpatch" \
  --output /absolute/new-source
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ml-sources/source.py \
  --package devel/ruy --sdk-source "$SDK_SOURCE" --git /usr/bin/git verify-source \
  --source /absolute/new-source --patch "$HOST_PREFIX/bin/gpatch"
```

The source-only packages do not select a target runtime or compile code. A consumer must preserve any required platform integration (such as Chromium's pthreadpool Jobs adapter), and must establish compatibility separately.
