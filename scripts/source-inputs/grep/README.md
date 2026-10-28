# Common grep source

Prepare the effective `textproc/grep` source from the Ports export and its
complete patch inventory using the selected SDK source-preparation API. The
helper applies the complete effective patch inventory and does not install a package.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/grep/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/grep-3.12.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --scoped-identity --output "$WORK/grep-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/grep/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/grep-source" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/grep-3.12.tar.xz"
```

If effective package inputs change, verification compares a freshly prepared
payload using the selected archive and patch. Runtime program paths remain a
consumer build setting; they are not hardcoded in this shared input.

GNU grep is licensed under GPL version 3 or later; see the prepared source's
COPYING and upstream notices. Its pkgsrc recipe retains its own option and
dependency policy; consumers select their build options explicitly.
