# H.265 RTP CPU SDK

This profile builds the installed FFmpeg/GStreamer C SDK used by the
[E35 interoperability example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/h265-rtp).
Use [results.md](results.md) for platform acceptance and recorded limitations.
A successful cross-build alone does not establish target execution.

The pinned providers are FFmpeg 9.0.2, GStreamer 1.28.8, GLib 2.90.1,
PCRE2 10.49, libffi 3.8.0, x265 4.2 and libxml2 2.15.4.
Archives and checksums come from [media sources](../sources.tsv),
[graphics sources](../../common-graphics/sources.tsv), and
[build-tool sources](../../common-build-tools/sources.tsv). Canonical recipe
patches are checksum-verified and applied with zero fuzz.

This is an explicit CPU selection. GStreamer enables app/video conversion,
typefinding/raw parsing, RTP, jitter buffering, UDP, H.265 parsing, x265 and
libav. FFmpeg retains its built-in CPU codecs/filters and selects shared x265
with `FFMPEG_X265=yes`. Ordinary desktop recipes retain their own options,
GUI/device integrations and dependency inventories. This SDK does not claim
hardware-codec, camera, GPU/NPU, RTSP or desktop playback acceptance.

## Prerequisites and order

Use matching EmberBSD base headers, libc, loader and runtime data in one
sysroot. Supported cross triplets are `aarch64--netbsd` and `x86_64--netbsd`.
Keep the CMake platform `NetBSD`. GCC and G++ must be 16.2.0.
The target sysroot needs GCC16 CRT objects, `libgcc_s.so.1`,
`libstdc++.so.7` and matching C++ headers under `/usr/pkg/gcc16`.
An older C++ runtime with a different SONAME is not interchangeable.
The target base runtime must include coherent `/usr/lib/i18n` modules and
`/usr/share/i18n` encoding/mapping data. GLib's error messages need conversion
between the C locale's `646`/US-ASCII and UTF-8. Headers and libraries alone
do not supply these runtime data.

Prepare target OpenSSL/compression/base dependencies, then libxml2, shared
x265, FFmpeg with x265, and GStreamer. Promote each dependency's staged
`usr/pkg` into the selected build sysroot before its consumers are configured.
Install their actual packages and runtime dependencies on the target as well.
See [the CPU cross-package prerequisites](../cross/README.md).

Build-host tools include native GCC16/G++, Ruby, Python 3 for upstream Meson
and generators, Ninja, CMake, GNU Make, pkg-config, patch, tar and checksum
utilities. FFmpeg also needs Perl, pod2man and makeinfo. Native and target
pkg-config providers must stay separate. Build a native GLib/GStreamer prefix
first; cross builds execute its generators, not target executables.
For a complete native media control prefix, install matching native x265 and
FFmpeg development libraries before building gst-bad and gst-libav.

## Helper interfaces

Run from this directory. Use absolute, simple paths without whitespace or
shell metacharacters. `CACHE`, `SYSROOT`, `GCC_PREFIX`, `NATIVE_PREFIX`,
`WORK` and `STAGE` below denote caller-selected paths.

```text
build-x265.sh native|cross ARCHIVES NEW_OUTPUT PREFIX
build-gstreamer.sh native ARCHIVES WORK PREFIX
build-gstreamer.sh cross ARCHIVES WORK STAGE SYSROOT TARGET GCC_PREFIX
../cross/build-libxml2.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT
../cross/build-ffmpeg-cpu.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT
```

`build-x265.sh` requires new output and uses `JOBS` (default 2). Cross mode
requires `GCC_PREFIX`, `SYSROOT` and `TARGET`; set `PREFIX` to `/usr/pkg`.
It stages the shared provider and CLI under `NEW_OUTPUT/stage/usr/pkg`.
Native mode also promotes its stage into the selected native prefix.

```sh
GCC_PREFIX="$GCC_PREFIX" SYSROOT="$SYSROOT" TARGET=aarch64--netbsd JOBS=2 \
  ./build-x265.sh cross "$CACHE" /absolute/new-x265-output /usr/pkg
cp -a /absolute/new-x265-output/stage/usr/pkg/. "$SYSROOT/usr/pkg/"
TARGET=aarch64--netbsd CROSS_JOBS=2 FFMPEG_X265=yes \
  ../cross/build-ffmpeg-cpu.sh "$GCC_PREFIX" "$SYSROOT" \
  "$CACHE/ffmpeg-9.0.2.tar.xz" /absolute/new-ffmpeg-output
```

The FFmpeg helper defaults to AArch64; set `TARGET=x86_64--netbsd` for AMD64.
`FFMPEG_X265` defaults to `no`, so enable it explicitly for E35.
`HOST_CC`/`HOST_CXX` select native GCC16; `CROSS_JOBS` controls parallelism.
The XML helper accepts the same `TARGET` and `CROSS_JOBS` settings.

```sh
JOBS=2 ./build-gstreamer.sh native "$CACHE" /absolute/native-gst-work \
  "$NATIVE_PREFIX"
NATIVE_PREFIX="$NATIVE_PREFIX" JOBS=2 ./build-gstreamer.sh cross \
  "$CACHE" "$WORK" "$STAGE" "$SYSROOT" aarch64--netbsd "$GCC_PREFIX"
NATIVE_PREFIX="$NATIVE_PREFIX" JOBS=2 COMPONENTS=gst-tests \
  ./build-gstreamer.sh cross "$CACHE" "$WORK" "$STAGE" "$SYSROOT" \
  aarch64--netbsd "$GCC_PREFIX"
```

`COMPONENTS` selects unique comma-separated names: `libffi`, `pcre2`, `glib`,
`gstreamer`, `gst-base`, `gst-good`, `gst-bad`, `gst-libav`, `gst-tests`. Selection follows
helper dependency order; it does not fetch missing prerequisites. The default
build excludes `gst-tests`. That explicit component builds the unchanged
upstream H.265 RTP and jitter-buffer tests against the installed SDK.
Native `CC`, `CXX`, `AR`, `RANLIB` and `STRIP` may select native tools.

The GStreamer helper preserves component work and reuses matching input/build
receipts. Changed source inputs/configurations require fresh work. Each stage
has logs, compile commands, `PASS.json`, an exact inventory and `PLIST`.
Licenses and `SOURCE` manifests are recorded before inventory and promotion.
Cross stages are promoted into both `STAGE/usr/pkg` and `SYSROOT/usr/pkg`.
Only recognized sysroot prefixes are normalized in libtool metadata and
manually installed test RPATHs; before bytes and change receipts are retained.
Unrecognized installed host paths cause failure. CMake supplies the test
RPATH installation transition.

Run upstream tests in a subshell with their required test environment:

```sh
(
GST_PLUGIN_LOADING_WHITELIST='gstreamer:gst-plugins-base:timecode:gst-plugins-good@/usr/pkg/lib/gstreamer-1.0/'
GST_PLUGIN_SYSTEM_PATH_1_0=/usr/pkg/lib/gstreamer-1.0
GST_PLUGIN_PATH_1_0=
GST_PLUGIN_SCANNER_1_0=/usr/pkg/libexec/gstreamer-1.0/gst-plugin-scanner
GSETTINGS_BACKEND=memory
export GST_PLUGIN_LOADING_WHITELIST GST_PLUGIN_SYSTEM_PATH_1_0 GST_PLUGIN_PATH_1_0
export GST_PLUGIN_SCANNER_1_0 GSETTINGS_BACKEND
unset CK_FORK
GST_REGISTRY_1_0=/absolute/new-h265.registry \
  /usr/pkg/libexec/emberbsd-rtp-tests/elements_rtph265
GST_REGISTRY_1_0=/absolute/new-jitter.registry \
  /usr/pkg/libexec/emberbsd-rtp-tests/elements_rtpjitterbuffer
)
```

The whitelist preserves upstream's provider selection while using installed
plugins. An absent whitelist fails the upstream environment beacon before
the test begins. Leave `CK_FORK` unset for default fork isolation; record any
larger `CK_DEFAULT_TIMEOUT` needed by emulation. Keep registries fresh.
This test whitelist excludes the libav/x265 providers used by the API suite;
do not export it into that suite's environment.

[tests/target-runtime-probe.c](tests/target-runtime-probe.c) diagnoses the
installed GLib/GIO error path independently of GStreamer. Compile with the
selected target compiler/sysroot and target `gio-2.0` pkg-config flags, then
run the resulting program without arguments. It prints libc/GLib encoding,
gettext, cancellation and empty-socket results; zero means its checked
contracts were present. Preserve output and status alongside runtime checks.

The selected x265 module reports GPL. gst-libav retains its wrapper COPYING
and all selected dependency notices; `GST_LIBAV_ENABLE_GPL=1` makes its plugin
metadata truthful for this GPL FFmpeg provider. FFmpeg's selected GPL/version3
configuration has GPL-3.0-or-later linkage. Read staged license texts before
redistributing a composed package.

## Acceptance and diagnostic scope

The example runs installed C APIs in both directions, seven bounded UDP
cases, deterministic packet faults, full pixel oracles and independent RTP
inspection. Its README explains local timestamps, loss recovery and receiver
teardown/rebind. Package lifecycle and actual per-platform outcomes belong
in [results.md](results.md).

Native GCC/Clang/Cppcheck diagnostics are bounded source checks. The memory
patch removes two baseline Clang undefined-value warnings. GCC retains
complexity-limit diagnostics. Cppcheck's inherited GLib cleanup-header parse
failure reproduces with a header-only control; this is not a clean whole-SDK
analysis claim. Native Memcheck separates raw results from narrowly justified
GLib TLS filtering; see the example's [exact controls and limits](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/h265-rtp/tests/memcheck).
Target runtime and native instrumentation are separate evidence.
