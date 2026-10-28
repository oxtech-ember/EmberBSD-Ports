# Shared 7-Zip source for firmware consumers

Prepare the source from the current `archivers/7-zip` recipe and its complete
patch set. The owner checks the archive against `distinfo`, uses the SDK flat
archive extractor, and applies the recipe's CRLF conversion before patches.
It does not build or install a package and does not require a target SDK.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/7zip/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/7z2605-src.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/7zip-source" --scoped-identity
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/7zip/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/7zip-source" --patch "$HOST_PREFIX/bin/gpatch"
```

When recipe or owner inputs change, supply the current `--archive` for a fresh
payload comparison. The output must not exist. Firmware integration supplies
its own freestanding ABI glue; this operation does not establish target runtime
or firmware boot behavior.
