# Common Node.js source

Prepare the effective `lang/nodejs` source from the Ports export, including all
recipe patches. The output is intended for consumers of the same Node source and patch set;
selecting an embedder and validating its runtime remain separate steps.
Source preparation does not build or install Node or establish runtime ABI.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/node-v26.13.0.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/node-source"
# Alternatively, prepare from an already exported pkgsrc tree without Git:
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" prepare --pkgsrc-root "$EXPORTED_PKGSRC" \
  --archive "$DISTFILES/node-v26.13.0.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/node-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" verify-source --source "$WORK/node-source" \
  --pkgsrc-root "$EXPORTED_PKGSRC"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" verify-payload --source "$WORK/node-source"
```

The archive name and checksums and the ordered patch inventory are read from
the exported recipe. The output must not exist. The current-recipe verifier checks the prepared payload and the effective package
in the caller-selected export; unrelated package changes do not invalidate it.
`verify-payload` checks only the recorded payload and makes no claim about the
current recipe. Patches must not be applied a second time.

## Configure shared inputs

`configure-inputs.py` prepares a writable Node source copy for either the common
package or an embedder. It validates the existing V8 and inspector prepared
source identities and verifies the selected GYP source against its pkgsrc export,
preserves the bundled V8 tree in the work directory, installs
a clean copy of the selected V8 source at `deps/v8`, and runs the selected V8
inspector roll. The Node source and work must be on the same filesystem and
must not overlap any selected provider. The selected work directory must already
exist. On an interrupted copy the original bundled V8 is retained as
`node-bundled-v8`; do not delete or overwrite it blindly.

The `prepare` action prints a JSON object containing the GYP arguments and the
`NODE_GYP_SOURCE` environment required for configure. The
`configure` action runs the Node source's original `configure` using the
selected Python, prepending the same shared GYP inputs to the caller's
configure arguments. The package uses `configure`; embedders can use either
without implementing another V8 overlay or inspector roll. Supply absolute
paths for the selected Node/work, GYP source and pkgsrc export, V8, inspector,
SDK, Jinja, zlib, host C++
wrapper, host Clang, libclang, Clang Python bindings and Clang resource
directory. For `configure`, place all original Node options after `--`.
Target compiler, target sysroot and embedder ABI remain caller-selected; this
helper does not change Node's default module version.

For the real NetBSD target regression, make a writable copy of the verified
Node source under a new work directory and select the target `CC`, `CXX`,
`AR`, `PKG_CONFIG` and ICU pkg-config inputs in the environment. Then run:

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/test-configure-inputs.py \
  --node-source "$WORK/node" --work "$WORK" --v8-source "$V8_SOURCE" \
  --inspector-source "$INSPECTOR_SOURCE" --sdk-source "$SDK_SOURCE" \
  --jinja-root "$JINJA_ROOT" --zlib-source "$ZLIB_SOURCE" \
  --gyp-source "$GYP_SOURCE" --gyp-pkgsrc "$PKGSRC_EXPORT" \
  --v8-cxx-wrapper "$HOST_PREFIX/libexec/cwrappers/c++-wrapper" \
  --v8-selected-clang "$HOST_PREFIX/bin/clang++" \
  --v8-libclang "$LIBCLANG" --v8-python-bindings "$HOST_PREFIX/share/clang-python-bindings" \
  --v8-clang-resource "$CLANG_RESOURCE"
```

The fixture checks real Node configure and GYP, clean V8 replacement, repeated
JSON output, selected GYP regeneration, and rejection of incorrect GYP identity, provider overlap and escaping `deps/v8` symlinks.
It checks Node's standalone ABI and NetBSD suffix; an embedder's generated
configuration and runtime require their own checks.
