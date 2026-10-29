# Common NTP source

Prepare and verify the full `net/ntp4` archive and effective patch set with
the selected SDK, Git and patch tools. The source is shared by the Ports
package and native OS integration; build options and target ABI are selected
by consumers. The NTP copyright and license are retained in `COPYRIGHT`.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ntp/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/ntp-4.2.8p18.tar.gz" --patch "$HOST_PREFIX/bin/gpatch" \
  --scoped-identity --output "$WORK/ntp-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/ntp/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/ntp-source" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/ntp-4.2.8p18.tar.gz"
```

When effective inputs change, verification prepares and compares the full
source payload. The host keyword generator consumes the parser header created
for its actual consumer; it does not use target headers in the host build.

The NTP package requires the separately prepared common AutoGen libopts source
in `EMBER_NTP_LIBOPTS_SOURCE`; see `pkgsrc/net/ntp4/README.md`. It uses the
shared external libevent package and refuses the embedded fallback. The OS
producer selects NTP and AutoGen source separately for its native integration.
