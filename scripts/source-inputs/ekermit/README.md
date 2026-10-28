# Common E-Kermit source

Prepare the current `comms/ekermit` archive and the complete Ports patchset
for a native OS consumer. The SDK source-preparation API handles the upstream
flat archive; the resulting directory contains `main.c`, `kermit.c`, `unixio.c`,
headers and the upstream BSD three-clause license. It does not install a package.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ekermit/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/ek18.tar" --patch "$HOST_PREFIX/bin/gpatch" \
  --scoped-identity --output "$WORK/ekermit-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ekermit/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/ekermit-source" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/ek18.tar"
```

When the effective recipe changes, verification compares the full freshly
prepared payload using the selected archive and patch. E-Kermit 1.8 corrects
the reversed binary and text transfer mode constants present in version 1.7.
