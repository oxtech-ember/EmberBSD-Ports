# SDR source and adaptation provenance

This profile was prepared with AI assistance on 2026-10-07. Project-owned shell,
C/C++ tests and synthetic fixtures use the accompanying MIT license. Existing
source copyright and license notices remain upstream's.

`sources.tsv` pins original upstream archives and one ABI declaration header by
SHA256. `patches.tsv` pins the adaptations. `patched-files.tsv` records upstream
and resulting file hashes. Source archives, build output and private machine
addresses are not repository content.

| Component | Upstream | Selected version | License |
|---|---|---|---|
| SoapySDR | https://github.com/pothosware/SoapySDR | soapy-sdr-0.8.1 | Boost Software License 1.0 |
| libiio | https://github.com/analogdevicesinc/libiio | v1.0.0, commit `9a929664fd3effa500430626803ac59ecf2f4ed3` | LGPL-2.1-or-later core; MIT/GPL notices for other files |
| libad9361-iio | https://github.com/analogdevicesinc/libad9361-iio | v0.3 | LGPL-2.1 |
| SoapyPlutoSDR | https://github.com/pothosware/SoapyPlutoSDR | soapy-plutosdr-0.2.2 | LGPL-2.1 |
| ABI 0 declaration header | libiio repository above | v0.26, commit `a0eca0d2bf10326506fb762f0eec14255b27bef5` | LGPL-2.1-or-later |

The installed ABI 0 library is compiled from **libiio 1.0.0's own `compat.c`**.
There is no libiio 0.26 runtime. Its older declaration header is isolated at
`include/iio-compat-0/iio.h`. Default headers remain libiio1's `include/iio/`;
the default `libiio` link name remains ABI 1. The shim loads that same current
runtime. Both old-API consumers explicitly use the private declarations and
`libiio.so.0`; neither gets an implicit global header replacement.

This transitional ABI surface is needed because AD9361 and SoapyPluto still use
the old channel-mask/buffer API. Replacing it requires a larger upstream API
migration. Remove the private header and shim requirement when both consumers
support the current API; do not substitute an older parallel runtime.
libad9361's **v0.3 source itself sets library version 0.2**, which this recipe
preserves rather than inventing a new upstream ABI version.

## Local patches, not accepted upstream

- `libiio-portability.patch`: use CMake's platform loader library instead of
  hardcoded `dl`; use the actual current library filename for non-framework
  builds. The original Darwin shim tries a framework path even with
  `OSX_FRAMEWORK=OFF` and crashes in its constructor. Host RED/GREEN proves this.
  The existing framework path remains intact when frameworks are enabled.
  Separately, correct NetBSD feature visibility and the three-argument
  `pthread_setname_np` call, passing the thread name as data through `%s`.
  The prototype is documented by [NetBSD](https://man.netbsd.org/pthread_setname_np.3).
  The exact upstream macro fails a host compile against this prototype; the
  patched macro passes. This is a signature regression, **not a native build**.
- `iiod-emu-loopback.patch`: add optional `--loopback` binding; keep upstream's
  default unchanged. Tests require the option. An actual socket `getsockname`
  contract verifies `127.0.0.1`. The upstream listener uses `INADDR_ANY`.
- `pluto-explicit-context.patch`: honor explicit URI/hostname before scanning,
  remove a process-global discovery result vector, give every device its own
  IIO context, and destroy streams before their context. Original discovery
  fails the installed explicit-URI contract. With discovery fixed but the
  original global context retained, the second device reports the first
  fixture's identity. Both failures were reproduced on upstream source bodies.
  Preserve signed RX return codes and distinguish failed I/O from timeout:
  a real empty emulator IQ source returns `-EIO`; upstream incorrectly reports
  `SOAPY_SDR_TIMEOUT`, while the patch reports `SOAPY_SDR_STREAM_ERROR`.

No patch is claimed to originate from pkgsrc or to be accepted upstream.
AppleClang already matches upstream's `GNU|Clang|MSVC` compiler test; no compiler
whitelist patch is needed. CMake 4 compatibility is enabled through the explicit
`CMAKE_POLICY_VERSION_MINIMUM=3.5` option for the older CMake entry points.

## External build dependencies and host evidence

CMake, Ninja, C/C++ compilers and Zstandard are provided by the build platform.
The common [libxml2 2.15.4 provider](../libxml2/README.md) is selected by required
`XML_PREFIX`. Its source inventory and explicit include/library paths are
checked and recorded. CMake caches/logs retain all dependency identities.
The source profile has no nested source download. DNS discovery, USB, serial,
local IIO, Python and MATLAB bindings, packaging and normal `iiod` are disabled.
Zstandard must be enabled: libiio1's network client requires it at configure.

Host evidence uses macOS arm64, Apple Clang 21, CMake 4.4.4 and Homebrew
Zstandard 1.5.7. The recipe builds against the project libxml2 2.15.4;
all installed RX contracts pass. Loader tracing confirms `XML_PREFIX/lib/libxml2.16.1.4.dylib`.
Native dependency versions/ELF/base-GCC ABI remain unverified.
No Python helper is introduced; the selected C/C++ build disables upstream
Python bindings. SoapySDR 0.8.1 still runs optional upstream Python discovery
and `get_python_lib.py` during configure, despite those disabled targets.
On the host this finds Python 3.14.8; its removed `distutils` import fails.
Upstream does not treat that optional probe as a configure failure, and no
Python binding or Python runtime dependency appears in the installed targets.
This profile does not claim to have removed the upstream configure probe.
The synthetic XML and deterministic signed IQ bytes are ours,
not copied device metadata or recorded RF signals.

## readStream deadline investigation

No general per-call deadline patch is claimed. The pinned upstream source
shows several independently relevant waits:

- SoapyPluto `readStream` takes `rx_device_mutex` before entering `recv`.
  `pluto_spin_mutex::lock` spins without a timed acquisition API. Time waiting
  behind another stream/control operation would escape a timeout loop in recv.
- libiio1 `compat.c` returns `-ENOENT` from `iio_buffer_get_poll_fd`; the official
  shim cannot supply a pollable descriptor. `iio_buffer_set_blocking_mode` only
  changes the boolean passed to `iio_block_dequeue`.
- The libiio1 network backend has an asynchronous dequeue path returning
  `-EBUSY` while work is incomplete, but the emu backend's `emu_dequeue_block`
  ignores its `nonblock` parameter. It can wait on `file_ready` for 5000 ms and
  then calls `fread`. A loop around that call cannot bound the call itself.

These are observed source properties in the SHA-pinned SoapyPluto 0.2.2 and
libiio 1.0.0 archives. A reliable solution needs deadline-aware stream ownership
plus a defined nonblocking/cancellation contract for the relevant backends and
tests for lock contention, stalled input, retry and clean shutdown. Altering
the shared context timeout does not satisfy those requirements. The existing
bounded TCP test remains a libiio context-creation test, not proof of a Soapy
stream deadline. This investigation leaves the runtime behavior unchanged.
