# Industrial I/O receiver library

This is the shared libiio 1.0.0 recipe for receiver consumers.
Upstream released tag `v1.0.0` on 2026-09-22 at commit
`9a929664fd3effa500430626803ac59ecf2f4ed3`.
The release and its official compatibility layer were checked on 2026-10-25.
Source URLs and SHA256 values are in [files/sources.tsv](files/sources.tsv).
Ordinary pkgsrc checksums and every patch are in [distinfo](distinfo).

The primary API is ABI 1 in `include/iio/iio.h` and `libiio.so.1`.
The default `libiio.so` link remains ABI 1.
The official `compat.c` from the same release provides `libiio.so.0`.
Only declarations from upstream v0.26 are installed at `include/iio-compat-0/iio.h`.
There is no legacy runtime. ABI 0 consumers must select that header and exact library.
The package includes LGPL core, GPL utilities and MIT emulator components with their notices.

The shared receiver configuration enables USB, network, XML and emulation.
USB is required; upstream configuration fails when libusb is missing.
It retains the network protocol fallback from BINARY/ZPRINT to legacy ASCII/PRINT.
It disables local Linux IIO, serial, discovery, ordinary IIOD and language bindings.
The Soapy probe consumes this same source, configuration and complete patch set.

## Local patches

The portability and optional emulator loopback patches moved from `probes/sdr`.
They preserve NetBSD feature visibility, its three-argument pthread naming API,
and the platform loader library. Framework behavior stays intact on Darwin.
The NetBSD shim has a stable SONAME, so exact library links do not embed build paths.

A legacy backend can return fewer bytes than a fixed block requests.
Upstream discards that count and reports a full block through its compatibility API.
The shared block guard returns `-EIO` for short data before exposing a stale tail.
It intentionally rejects partial blocks; it does not invent or pad samples.
Cancellation interrupts the backend before waiting for the worker to stop.
Otherwise a blocked read waits for its transport timeout before cancellation can run.
On NetBSD, core and compatibility cleanup use DSO destructors instead of process
`atexit` handlers. The shim unloads the core; a later process callback would jump
into the unmapped core. Applications can also unload the shim explicitly.
Actual NetBSD tests reproduced both failures after four load/unload cycles and
confirmed normal exit with the DSO lifetime fix. Other platforms retain their
upstream registration behavior.
These changes are EmberBSD work with AI assistance and are not submitted upstream.

## Checks and cross staging

Use the selected GCC16 tools and the helpers under
[profiles/sdr-receivers](../../../profiles/sdr-receivers/README.md#industrial-io).
The standalone legacy peer and C consumer exercise actual installed core and shim:
attributes, full IQ bytes, incomplete data, I/O errors, blocked cancellation and close.
The lifetime fixture additionally loads/unloads each actual ABI four times,
then exits normally; it resolves a symbol without mixing the two API signatures.
They require no receiver or private sources. Native/target and physical acceptance are separate.
