# Native U-Boot image tools

`u-boot-tools` builds and installs `mkimage` and `dumpimage` from the exact
revision of the common `u-boot-source` package. It uses the native libfdt and
OpenSSL packages. The shared source includes the common zlib sources; these
two tools do not link a separate zlib library in the checked native build.
The tools-only configuration disables the unrelated EFI capsule generator.
This package builds for the native host. Cross-build consumers select the
native package through `TOOL_DEPENDS`; direct cross-building of this package
is not supported.

To check a native build, use the selected host Python and prefix:

```
"$HOST_PYTHON" tests/fit-roundtrip.py \
    --host-prefix "$HOST_PREFIX" --mkimage "$MKIMAGE" --dumpimage "$DUMPIMAGE"
```

The check creates an external-data FIT, verifies its SHA-256 property and
compares the extracted payload. It does not test booting a target device.
