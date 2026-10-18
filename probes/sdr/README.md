# Ethernet SDR source and RX software probe

This profile builds SoapySDR 0.8.1, libiio 1.0.0, libad9361-iio v0.3 and
SoapyPlutoSDR 0.2.2 into one disposable prefix. It prepares the software path
for a Pluto/AD9361 Ethernet receiver. The current result is **host software
validation on macOS arm64**. Native EmberBSD/NetBSD and a physical PlutoSky7020
AD9361 board remain untested.

The library versions are the selected upstream stable releases, rather than
older package versions chosen for compatibility. See [PROVENANCE.md](PROVENANCE.md)
for licenses, origins, the ABI exception and regression evidence.

## One current IIO runtime

Both radio consumers still use the libiio 0 API. This profile builds the
**official compatibility library from libiio 1.0.0 itself**. `libiio.so.0`
forwards to the same current ABI 1 runtime. There is no older IIO runtime.
The v0.26 declaration header is pinned and isolated in `include/iio-compat-0`;
only the two old-API consumers explicitly use it. Default headers and the
ordinary link name remain libiio1. Remove this transitional header/shim surface
when both upstream consumers support the new channel-mask and buffer API.

The profile enables network, XML, emulator, Zstandard and shared libraries.
It disables local IIO, USB, serial, discovery, ordinary `iiod`, language bindings
and packaging. `iiod-emu` is included solely for software contracts and has a
new `--loopback` option. The tests always use that option.

## Build and test

Native prerequisites are base C/C++ compilers, CMake, Ninja, curl (unless using
a complete cache), the common [libxml2 2.15.4 provider](../libxml2/README.md) and
Zstandard. `XML_PREFIX` is required and names that provider's installation.
Its source inventory is checked and its exact include/library paths are used;
there is no fallback to an older SDK or `/usr/pkg` XML library. For Zstandard,
`DEPENDENCY_PREFIX` defaults to `/usr/pkg`; override that variable,
`LIBZSTD_INCLUDE_DIR` or `LIBZSTD_LIBRARIES` when needed. Native dependency/ABI
validation remains pending.

```sh
CC=/usr/bin/cc CXX=/usr/bin/c++ CMAKE=/usr/pkg/bin/cmake JOBS=1 \
    XML_PREFIX=/absolute/common-xml-work/install \
    ./build.sh /absolute/new-sdr-work /absolute/pinned-cache
./test.sh /absolute/new-sdr-work
```

The cache contains every filename in [sources.tsv](sources.tsv), including the
single ABI declaration header. Without a cache argument the recipe downloads
those exact URLs. It checks SHA256 before extracting and before applying each
patch. It also checks the original and patched source-file hashes. There is no
nested source fetch. Work must be a new absolute path without spaces.
`tar -m` avoids clock-skew regeneration loops after recipe transport.

`JOBS` defaults to 1. Memory limits are inherited. Only an explicitly supplied
positive `BUILD_AS_KIB` changes the process's soft address-space limit; there is
no default memory ceiling. The caller manages shared-machine disk space and
build scheduling. All installation paths stay under the selected work directory.

For the tested macOS arm64 host configuration, use `HOST_CHECK=1`; the recipe
uses the same required `XML_PREFIX` and `/opt/homebrew` Zstandard.
This host path is a software check, not a cross-build for NetBSD. Soapy's
upstream configure still probes Python despite disabled binding targets;
[provenance](PROVENANCE.md#external-build-dependencies-and-host-evidence) records
the observed Python 3.14.8/removed-distutils probe failure and its scope.

## Contracts and actual results

The host run uses Apple Clang 21.0.0, CMake 4.4.4 and Ninja 1.13.2.
A fresh source-cache build and the complete installed-consumer test script
pass against the common libxml2 2.15.4 provider. The tests use two small synthetic XML contexts and a generated,
deterministic 4096-sample signed IQ file. No RF recording or hardware metadata
is needed.

- C ABI 0 consumer: current runtime version, attribute write/read, missing
  attribute error and 64 exact complex samples, through both `emu:` and loopback
  `ip:` contexts.
- Installed Soapy C++ consumer: explicit URI without discovery; missing,
  malformed and non-Pluto contexts rejected; independent context identities and
  attributes; destruction of one device leaves the other usable; unsupported
  sample format rejected.
- RX conversion: CS16 values and CF32 division by 2048 match scalar expected
  values across reads of 17, 47, 29 and 35 samples. These reads cover buffer tails
  and a refill boundary. Only RX streams are opened.
- Failed RX source: an empty IQ file is a stream error, not a timeout.
- Network behavior: socket identity proves a loopback-only emulator listener;
  two installed emulators supply the same numerical RX contracts. A separate
  silent TCP server accepts connection but sends no protocol response. libiio1
  with a 100 ms per-operation timeout returns `ETIMEDOUT` in about 204 ms; a
  closed listener returns `ECONNREFUSED`.
- Build guards reject relative/existing work paths, invalid jobs/explicit
  limits, corrupt archives and patches, and a missing installed inventory.

All test failures retain nonzero status. Logs and installed SHA256 inventory
are written below the work directory. On macOS, loader tracing confirms
`libiio.so.0` and ABI 1 both come from this prefix; linked Soapy/AD9361 libraries
and the system C++ runtime are recorded. The trace also confirms the common
libxml2 2.15.4 provider from `XML_PREFIX`, not the system XML library.
Native ELF/base-GCC ABI checks remain
pending. The thread-name adaptation has a source-level RED/GREEN signature
regression, not native validation.

The recipe owner is EmberBSD-Ports. The public overview should describe this as
a prepared source profile with host RX contracts until native and board results
exist. It must not describe usable hardware SDR support yet.

## Boundaries before hardware use

The [PlutoSky Ethernet handoff](HARDWARE.md) gives the native prerequisites,
explicit-endpoint inspection and the evidence required for the next RX stage.

No network discovery, board access, RF transmission, firmware change or device
installation is performed by these tests. The board endpoint has not been
supplied. Future board work must use the explicitly supplied Ethernet URI;
these fixtures do not establish radio tuning, RF performance, sample throughput,
clock accuracy, continuous capture, USB or transmission support.

SoapyPluto 0.2.2 still ignores `readStream`'s requested `timeoutUs`; its underlying
IIO context timeout governs refill. The bounded silent-server test establishes
libiio1 context-creation behavior, not a Soapy per-call stream deadline. This
limitation remains open before relying on application-level RX deadlines.
The [source audit](PROVENANCE.md#readstream-deadline-investigation) explains why
changing a context timeout or adding a simple poll loop would not establish a
general per-call deadline for this stack.
Attribute writes on a synthetic context also do not prove AD9361 calibration.
The plugin retains upstream TX code, but no TX stream or RF transmission is
part of this profile's validated scenario.
