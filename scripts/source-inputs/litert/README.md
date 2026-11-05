# Common LiteRT source

The `devel/litert` Ports recipe owns the upstream release and patch set. This
source-only producer uses the shared SDK prepared-tree API and Ports archive
helper; it does not build LiteRT or select an inference backend. Select the SDK,
Git and patch executables explicitly and supply the verified upstream archive.
The output receipt identifies the owner and complete upstream prepared payload.
The optional source package excludes upstream LFS pointers to prebuilt runtime binaries while
retaining the adjacent build metadata; consumers build with selected tools.
Existing output
is never overwritten.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/litert/source.py \
  --sdk-source "$SDK_SOURCE" --git /usr/bin/git prepare \
  --archive /absolute/LiteRT-2.3.2.tar.gz --patch "$HOST_PREFIX/bin/gpatch" \
  --output /absolute/litert-source
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/litert/source.py \
  --sdk-source "$SDK_SOURCE" --git /usr/bin/git verify-source \
  --source /absolute/litert-source --patch "$HOST_PREFIX/bin/gpatch"
```

Chromium integration and LiteRT's other source dependencies are separate
consumer contracts; a source receipt does not establish runtime, ABI or target
execution compatibility. LiteRT 2.3.2 uses `tflite/` paths: Chromium's adapter
and selected TensorFlow/XLA inputs need validation against this release.
