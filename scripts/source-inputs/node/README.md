# Common Node.js source

Prepare the effective `lang/nodejs` source from the Ports export, including all
recipe patches. The output is intended for consumers of the same Node source and patch set;
selecting an embedder and validating its runtime remain separate steps.
Source preparation does not build or install Node or establish runtime ABI.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/node-v26.12.1.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/node-source"
# Alternatively, prepare from an already exported pkgsrc tree without Git:
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/node/source.py \
  --sdk-source "$SDK_SOURCE" prepare --pkgsrc-root "$EXPORTED_PKGSRC" \
  --archive "$DISTFILES/node-v26.12.1.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
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
