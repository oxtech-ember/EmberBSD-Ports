# Native DRM change events

The libudev-bsd 0.7.0.1nb3 recipe accepts native DRM card changes through
the existing ndevd transport. It also sets `drm_minor` for primary and render
nodes. KWin 6.8 filters monitor events by both `drm` and `drm_minor`.
The earlier nb2 recipe supplied the subsystem but no device type.
Its native parser accepted only device attachment and removal.

This repairs the common provider. It does not implement a display driver,
detect a connected monitor, read EDID or program display timings.
Physical HDMI hotplug and accelerated presentation require separate acceptance.
The public libudev ABI and ndevd packet layout are unchanged.

## Producer contract

The OS DRM producer publishes these three strings through `devmon_insert_vec`:

| Field | Value |
| --- | --- |
| `event` | `device-change` |
| `device` | `dri/cardN`, using the registered primary minor index |
| `parent` | The real autoconfiguration device name |

The producer must retain a live registered device with a primary minor.
It runs in process context after detection and makes no mode-setting callbacks.
The event requests a fresh KMS state query. It does not remove the GPU.
Do not substitute a render minor or manufacture an attach/remove pair.

ndevd 25.12.09 forwards three 65-byte character arrays: `event`, `device`
and `parent`. The record is 195 bytes. Each field is NUL-terminated.
Existing device hooks act on attachment or removal, so this event does not
invoke MAKEDEV. The bounded kernel queue can discard old events.
Consumers must discover initial state and query current connector state.
An event is not a persistent log of every physical transition.

The library accepts `device-change` only for exact decimal `dri/cardN` paths.
It converts that event to the existing `UD_ACTION_HOTPLUG` action, exposed
as `change`. Existing valid attach/remove events retain their behavior.
The parser rejects short, oversized and unterminated records.
One extra receive byte detects a truncated oversized `SOCK_SEQPACKET` record.
The parser rejects an output buffer that cannot hold the complete path.

KWin's existing `DrmBackend::handleUdevEvent` handles primary-node `change`
events and calls `updateOutputs`. It then queries the connector properties.
A primary node without KMS is still rejected by `drmIsKMS`.

## Source contract

Use the pinned source archives and a new output directory:

```sh
ruby profiles/common-graphics/tests/libudev-drm-events.rb \
  /absolute/distfiles/libudev-bsd-0.7.0.1.tar.gz \
  /absolute/distfiles/ndevd-25.12.09.tar.gz /absolute/new-contract-output
CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' \
  ruby profiles/common-graphics/tests/libudev-drm-events.rb \
  /absolute/distfiles/libudev-bsd-0.7.0.1.tar.gz \
  /absolute/distfiles/ndevd-25.12.09.tar.gz /absolute/new-sanitized-output
```

The runner checks archive and patch hashes. Its baseline includes both nb2
patches. That baseline must reject primary changes and fail the real
`drm_minor` filter. The changed source checks exact card identity, invalid
paths, attach/remove preservation, unknown events, every short record length,
oversized records, missing terminators and output capacity.
A negative control restores the original receive capacity and must detect
a lost oversized-record boundary.
It compiles the actual native parser and path mapper without replacements.
The classifier, filter, list and utility files are compiled directly.
Unrelated hardware/property callbacks abort if reached.

The packet-boundary check uses a real local socket pair and the receive
buffer declaration extracted from the production monitor loop.
Darwin lacks UNIX `SOCK_SEQPACKET`, so that host uses `SOCK_DGRAM` explicitly.
This models record boundaries; it does not certify the native daemon transport.
Other hosts use `SOCK_SEQPACKET`. This check does not run the full monitor thread.
The existing [render-node and sysctl tests](libudev-render-nodes.md) remain required.

The four reviewed target translation units pass GCC 16 path analysis and
Clang Static Analyzer with the retained nb2 configuration and EmberBSD headers.
Cppcheck 2.22 on the GCC-preprocessed C units retains the baseline macro,
header and style findings; it introduces no new findings. No categories are
disabled. This comparison is not a clean Cppcheck result.
ASan/UBSan host checks supplement the source contract.
Valgrind Memcheck is unavailable on macOS/arm64; this is not a Valgrind result.
Installed ndevd delivery, a live kernel producer, KWin output refresh and
physical display behavior remain separate gates.

## Sources

- [libudev-bsd v0.7.0.1](https://github.com/kikadf/libudev-bsd/tree/v0.7.0.1),
  especially `udev-dev.c`, `udev-monitor.c`, `udev-utils.c` and `udev-filter.c`.
- ndevd 25.12.09: `ndevd.h` and `devpubd.c`; the runner verifies its archive SHA256.
- [KWin 6.8.0](https://invent.kde.org/plasma/kwin/-/tree/v6.8.0),
  `src/backends/drm/drm_backend.cpp` and `drm_gpu.cpp`.

The adaptation is AI-assisted and local. It is not an upstream acceptance.
