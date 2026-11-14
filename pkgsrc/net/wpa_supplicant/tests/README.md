# wpa_supplicant adapter tests

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
