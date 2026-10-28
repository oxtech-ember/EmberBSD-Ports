# Shared Brotli source for firmware consumers

Prepare the source from the current `archivers/brotli` recipe and its complete
patch set. The owner verifies the archive against the exported recipe and uses
the shared SDK source extractor. It does not build or install a package and does
not require a target SDK. This source supplies internal headers for the host
firmware compressor; target integration needs its own freestanding ABI glue.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/brotli/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/brotli/brotli-1.2.1.tar.gz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/brotli-source" --scoped-identity
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/brotli/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/brotli-source" --patch "$HOST_PREFIX/bin/gpatch"
```

When recipe or owner inputs change, supply the current `--archive` for a fresh
payload comparison. The output must not exist. Preparation does not establish
target runtime or firmware boot behavior.
