# mDNSResponder source for the native OS build

Origin: EmberBSD (AI-assisted).

Use this owner to prepare the same upstream archive and complete patch set as
`net/mDNSResponder`. Select the SDK source, Git inspector, native patch tool,
downloaded archive and a new output directory explicitly. For example:

```
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/mdns/source.py --sdk-source "$SDK_SOURCE" \
  --git "$GIT" prepare --archive "$ARCHIVE" --patch "$PATCH" \
  --scoped-identity --output "$OUTPUT"
```

An optional `--pkgsrc-export` reuses a compatible shared export. The generated
source receipt is selected by the SDK's `--mdns-source` and passed to the OS
as `EMBER_MDNS_SOURCE`. This prepares source; it does not build the daemon.
