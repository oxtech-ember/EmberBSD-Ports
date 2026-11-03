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

For unchanged prepared payloads, `refresh-source --source "$OUTPUT" --archive
"$ARCHIVE" --patch "$PATCH"` verifies the payload and current source identity,
then atomically updates its receipt to the current scoped identity. Supply
`--pkgsrc-export` when using a shared export. The caller must hold exclusive
use of the prepared source throughout verification and refresh; this command
does not acquire that lock. A failed verification leaves the receipt unchanged.
