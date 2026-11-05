# Common OpenXLA and TSL sources

The `devel/openxla` Ports recipe owns the shared OpenXLA source snapshot and
patches. OpenXLA publishes no stable release tags; the selected source is a
single explicitly dated upstream Git commit, not a TensorFlow or LiteRT binary.
Update the common owner and affected consumers together.

The source-only producer uses the existing Ports archive helper and SDK
prepared-tree API. It checks archive checksums and the effective recipe,
preserves the archive's safe internal relative symlink, and creates a receipt
for the complete prepared payload. It does not compile a runtime or establish
consumer API, ABI, platform or target compatibility.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/openxla/source.py \
  --sdk-source "$SDK_SOURCE" --git /usr/bin/git prepare \
  --archive /absolute/xla-13cab0c9fd4224a9f397f30b575f783b2c3da980.tar.gz \
  --patch "$HOST_PREFIX/bin/gpatch" --output /absolute/openxla-source
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/openxla/source.py \
  --sdk-source "$SDK_SOURCE" --git /usr/bin/git verify-source \
  --source /absolute/openxla-source --patch "$HOST_PREFIX/bin/gpatch"
```
