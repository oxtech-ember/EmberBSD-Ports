# CIX P1 codec: media build prerequisites

This work prepares the media side of a native stateful V4L2 M2M driver.
It does not provide a working CIX P1 hardware codec.
The existing native `video(4)` framework supplies capture devices only.
A CIX codec driver must own separate input/output queues, firmware,
interrupts and DMA lifetimes before hardware acceptance can start.

The common provider remains FFmpeg 9.0.2 and GStreamer 1.28.8.
Their original archive URLs and hashes are in [sources.tsv](../sources.tsv).
No older vendor fork or retired DKMS module replaces these providers.
The changes and diagnostics are AI-assisted EmberBSD work.
Original FFmpeg, GStreamer and pkgsrc licences and attribution remain intact.
No upstream submission or acceptance is claimed.

## Native API selection

FFmpeg `9.0.2nb3` selects `<sys/videoio.h>` for stateful M2M modules on
EmberBSD. Configure probes the same header used by the implementation.
The Linux header path remains in use on Linux.
HEVC registration requires the native `V4L2_PIX_FMT_HEVC` definition.
The diagnostic refuses a sysroot without it instead of defining a substitute.

The patch also repairs reference-semaphore lifetime. Previously, cleanup ran
`sem_destroy` even when no device had caused `sem_init` to run.
That path crashes with NetBSD's pointer-based semaphore representation.
The semaphore now initializes once, before probing. Initialization errors
propagate, and cleanup destroys only a successfully initialized semaphore.
The same fix prevents repeated device probes from reinitializing a live semaphore.

GStreamer's existing upstream V4L2 plugin already supports BSD builds.
Without GUdev, it scans `/dev/video0` through `/dev/video255` and `/dev/v4l2/video*`.
It registers HEVC factories only after a real M2M device advertises matching caps.
No GStreamer codec implementation or device discovery stub was added.
The selected AArch64 ABI probe compares nine structure sizes, four member
positions and 45 ioctl numbers between native and bundled headers.
This limited comparison does not establish the complete API or DMA semantics.

## Cross-build diagnostics

Prepare sources with the canonical common-media recipes first.
The target compiler wrapper must select GCC 16.2.0 and an explicit EmberBSD sysroot.
The build host also uses GCC 16.2.0. Target systems execute the results only.

```sh
sh profiles/common-media/cix-vpu/probe-header-abi.sh \
  GCC_PREFIX SYSROOT PATCHED_GST_GOOD_SOURCE NEW_ABI_RESULTS
sh profiles/common-media/cix-vpu/tests/ffmpeg-cross.sh \
  PATCHED_FFMPEG_SOURCE TARGET_CC HOST_CC NEW_FFMPEG_RESULTS
CC_FOR_BUILD=HOST_CC CXX_FOR_BUILD=HOST_CXX \
  sh profiles/common-media/cix-vpu/tests/gstreamer-cross.sh \
  PATCHED_GST_GOOD_SOURCE MESON_SOURCE CROSS_FILE TARGET_CC NEW_GST_RESULTS
```

Use absolute paths. The GStreamer check uses the common Meson 1.12.1 source.
Its cross file and pkg-config environment must select the installed common
GStreamer 1.28.8 and GLib dependencies. It installs into a private staging tree.
It preserves the upstream V4L2 implementation and all its codec modules.
These are focused diagnostics, not complete FFmpeg or GStreamer package acceptance.

`ffmpeg-cross.sh` builds only stateful HEVC encoder/decoder support.
The software HEVC decoder is disabled. It creates two target executables:

- `ffmpeg-no-device`: four real encoder and four decoder initialization refusals.
  Each refusal must return `EINVAL` and emit the actual missing-device diagnostic.
- `ffmpeg-semaphore`: normal missing-device cleanup and injected POSIX
  `sem_init` failure for both codecs. It checks initialization/destruction counts.
  Link-time semaphore wrappers test lifetime only; they do not emulate a device.

Compile `tests/gstreamer-no-device.c` with the target `gstreamer-1.0` C API.
On a system without M2M hardware, pass the staged plugin's absolute path.
It requires successful loading and ordinary V4L2 registration, with no HEVC factory.
Use a private plugin registry and empty plugin search paths for this check.
No hardware-free diagnostic can establish H.265 pixels, throughput or power use.

## Recorded scope

GCC16 cross-builds pass for the actual FFmpeg M2M backend and all 36 C files
of the upstream GStreamer V4L2 plugin. Meson installation removes host paths
from its runtime search path. All 58 selected AArch64 ABI values match.
The old-header refusal and zero-fuzz application of all 21 FFmpeg patches pass.
The complete `nb3` package and its consumers have not been requalified.
Earlier CPU package results retain their original versions and scope.

The semaphore regression rejects the real pre-fix FFmpeg archive on Linux.
The fixed implementation passes both normal cleanup and initialization failure.
Linux Memcheck finds zero errors, zero leaked bytes and no remaining heap
in these FFmpeg checks. This supported-host run does not replace EmberBSD execution.
The actual native GStreamer plugin loads without a HEVC factory on Linux.
Its strict Memcheck run retains upstream GLib/GType process globals;
[analysis and limits](analysis.md) records this result without suppressions.

CIX firmware execution, kernel attachment, hardware encode/decode, stream
reset, concurrent clients and sustained operation remain unverified.
