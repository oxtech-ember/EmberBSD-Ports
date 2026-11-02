# Bosch BMM150 SensorAPI source

Upstream: `boschsensortec/BMM150_SensorAPI`, release 2.0.0 at commit
`0dce0617873cda1f6d51f6b7b961fdc2641e0c7c`, downloaded from the exact commit
archive. Copyright Bosch Sensortec GmbH, BSD-3-Clause; retain the upstream
`LICENSE` with the installed source.

The Ports patch set adds NetBSD kernel type-header support and maps failed bus
callbacks to `BMM150_E_COM_FAIL`. The latter is required so callers do not
mistake a failed I2C transfer for a successful register operation. Both patches
are carried by this source owner and apply to every consumer.

The regression in `tests/t_bmm150_api.py` compiles the patched API against a
mock bus and checks transport-error propagation and compensation. It accepts
the installed source directory explicitly:

```sh
python3 -B tests/t_bmm150_api.py --cc /path/to/clang \
    --source-dir /path/to/share/bmm150-sensorapi --out-dir /tmp/bmm150-api-test
```
