# wpa_supplicant adapter tests

`t-radius-message-authenticator.py` compiles the prepared `src/radius/radius.c`
with its real buffer, OS, and MD5 helpers. It checks exact 18-byte values in
both RADIUS verifiers; short, oversized, and parser-truncated attributes are
rejected. The DAS request uses a valid Request Authenticator so the test
reaches the production Message-Authenticator check.

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/wpa_supplicant/tests/t-radius-message-authenticator.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --host-sdk "$HOST_SDK" \
    --source "$WPA_SOURCE/src/radius/radius.c"
```

Run again with
`--cflags='-O1 -g -Wall -Wextra -fsanitize=address,undefined -fno-sanitize-recover=all'`
to check malformed lengths against memory bounds. Add
`--emit-c "$WORK/radius-message-authenticator.c"` to retain the harness for
Cppcheck or Clang Static Analyzer.

`t-rrm-association-state.py` executes the prepared non-SME association
handoff, the EVENT_ASSOC request-IE update prefix, and the actual Neighbor
Report command gate. It checks that request IEs override the association
parameter when present (including when response IEs are absent), malformed
request IEs fail closed, and absent request IEs preserve the association
parameter. It also covers failed association construction, the not-completed
command gate, and the `CONFIG_NO_RRM` build guard. It executes the unchanged SME
association helper as a control and checks the command's not-completed state
gate.

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/wpa_supplicant/tests/t-rrm-association-state.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --host-sdk "$HOST_SDK" \
    --wpa-source "$WPA_SOURCE/wpa_supplicant/wpa_supplicant.c" \
    --events-source "$WPA_SOURCE/wpa_supplicant/events.c" \
    --rrm-source "$WPA_SOURCE/wpa_supplicant/rrm.c" \
    --sme-source "$WPA_SOURCE/wpa_supplicant/sme.c"
```

Repeat with `--no-rrm` to compile the extracted paths with
`CONFIG_NO_RRM` enabled.

`t-rsn-port-authorize.py` checks the prepared 2.12 RSN M3 path and executes
the production EAPOL authorized-state callback. RSN port authorization must
remain closed until GTK/IGTK setup succeeds. The no-GTK completion branch is
executed; the non-PMF IGTK helper's no-op guard and WPA1/group-rekey paths are
checked as unchanged source controls.

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/wpa_supplicant/tests/t-rsn-port-authorize.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --host-sdk "$HOST_SDK" \
    --wpa-source "$WPA_SOURCE/src/rsn_supp/wpa.c" \
    --eapol-source "$WPA_SOURCE/src/eapol_supp/eapol_supp_sm.c"
```

Run once with the default optimized flags and once with
`--cflags='-O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all'`.
Use `--emit-c /tmp/rsn-port-order.c` to retain the extracted C harness for
Cppcheck or Clang Static Analyzer.

`t-bsd-sta-scan.py` extracts and executes the BSD adapter's production scan
request, completion, cancellation, and disconnect paths. Its source must be
the `src/drivers/driver_bsd.c` produced by the canonical WPA 2.12 source
preparation recipe, including the current Ports patch set.

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/wpa_supplicant/tests/t-bsd-sta-scan.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --host-sdk "$HOST_SDK" \
    --source "$WPA_SOURCE/src/drivers/driver_bsd.c"
```

`t-bsd-association-epoch.py` executes the patched MLME version helper and
association-event lifecycle helpers, including unaligned input, current and
stale disconnects, autonomous retirement before ASSOC, same-epoch BSSID
validation, and interface-lifetime reset. Use the same prepared source tree:

```sh
"$HOST_PREFIX/bin/python3.15" -B pkgsrc/net/wpa_supplicant/tests/t-bsd-association-epoch.py \
    --cc "$HOST_PREFIX/bin/clang" \
    --host-sdk "$HOST_SDK" \
    --source "$WPA_SOURCE/src/drivers/driver_bsd.c"
```

Run once with the default optimized flags and once with
`--cflags='-O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all'`.
