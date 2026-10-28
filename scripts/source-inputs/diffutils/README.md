# Common diffutils source

Prepare the effective `devel/diffutils` source from the Ports export and its
complete patch inventory using the selected SDK source-preparation API. The
helper also supplies the common recipe's configure diagnostics file and pairs
generated-source timestamps as the recipe does; it does not install a package.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/diffutils/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/diffutils-3.12.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --scoped-identity --output "$WORK/diffutils-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/diffutils/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/diffutils-source" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/diffutils-3.12.tar.xz"
```

If effective package inputs change, verification compares a freshly prepared
payload using the selected archive and patch. Runtime program paths remain a
consumer build setting; they are not hardcoded in this shared input.
