# Four-stream Qt CPU media validation

Validation date: 2026-10-16. Source and checks are AI-assisted.

## Build and runtime selection

GCC/G++ 16.2 cross-compile Qt 6.12.0 and the C++17 viewer for EmberBSD
amd64. The coherent base comes from EmberBSD source
`c5d396f5698b68e956b29ee5b256bc7877e6c517`, release
`build-c5d396f5698b68e956b29ee5b256bc7877e6c517-amd64-no-x11`.
The base compiler is GCC 12.5. Application packages use GCC16 and its
`libstdc++.so.7`; this does not describe a GCC16 base-system rebuild.

The common providers are FFmpeg 9.0.2nb2, x265 4.2, GLib 2.90.1,
PCRE2 10.49, libffi 3.8.0nb1 and libxml2 2.15.4nb1.
The Qt CPU selection adds PNG 1.6.59, FreeType 2.14.3nb1,
HarfBuzz 14.6.0nb1, QtBase 6.12.0nb3, QtShaderTools 6.12.0 and
QtMultimedia 6.12.0nb2. It uses the FFmpeg multimedia backend and
the raster VNC QPA plugin. It requires no target audio server or GPU.
Matching native Qt generators run on the Linux build host.

This profile is separate from the full desktop Qt package selection.
`package-runtime.rb WORK STAGE SYSROOT NEW_OUTPUT` prepares six runtime-only
payloads and exact dependency metadata from completed producer receipts.
It checks ELF architecture, library ownership, RPATHs and SONAME closure.
Pass an explicit native `pkg_create` as its optional fifth argument, or
create the packages with target `pkg_create` from the prepared inputs.
The target needs package tools, not a compiler or build dependencies.

## Port fixes

- Qt Multimedia can select FFmpeg on NetBSD without an audio backend.
  Thread support and an actual FFmpeg provider remain required.
  Ninety-six feature-condition combinations and twelve recipe cases pass.
- The PulseAudio native prerequisite checks `dgettext` through `libintl.h`
  before requiring an external intl library. Actual native and cross-link
  controls preserve the platforms that need `-lintl`.
- QtBase's backtrace fallback accepts the actual pointer constness,
  handles allocation failure and requests a NetBSD symbol format that its
  parser understands. The installed QtCore API probe finds its real marker
  and exported call-site symbol in the target VM.
- The VNC screen has one initializer and releases its dirty map.
  Memcheck reproduced the upstream duplicate allocation and retained
  framebuffer. The corrected actual plugin passes the same viewer lifecycle.
- CMake module linking selects GCC16 for plugins as well as executables
  and shared libraries. The actual target plugins depend on
  `libstdc++.so.7`; a successful shared-library link alone did not prove this.

## Inputs and display checks

The [example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/qt-four-streams)
uses four actual QMediaPlayer/QVideoSink pairs in one 1280×800 QWidget.
Each input is H.265, 2048×1500, 9 fps, with a different lossless I420 pattern.
Both the 36-frame and 180-frame sets pass independent native decoding,
whole-stream SHA256 comparisons and exact source-timestamp checks.
The viewer verifies every active decoded luma and chroma byte and frame ID.
An independent RFB client reads the actual displayed framebuffer.

Sink handoff is bounded to eight frames per stream. Overflow is counted;
strict acceptance still fails if any expected source frame is absent.
The SDR BT.709 CPU path scales decoded YUV to the viewport before RGB
conversion through the current FFmpeg `sws_scale_frame` API.
Full-resolution decoding and the independent pixel oracle remain enabled.

The initial target run exposed unbounded queued frame retention and GUI
starvation. Both 36-frame runs decoded and verified every frame, but each
quadrant painted only twice. The 180-frame run exhausted a 2 GiB guest.
These failures motivated the bounded handoff and viewport conversion.
They are retained as failed evidence, not counted as accepted display runs.

The corrected native Linux control decodes, verifies and paints all 180
frames per stream in 20.167 seconds. Observed paints are 9.038–9.059 fps.
CPU use is 57.57% of one core, including pixel checks and display work.
Each mailbox peaks at one or two frames, with zero coalescences.
This native result does not establish EmberBSD target throughput.

## Analysis and limits

GCC16 strict warnings pass for native and target builds. The C generator's
GCC `-fanalyzer` check and the full viewer's Clang19 analyzer report no
diagnostics. The actual changed VNC and backtrace translation units also
retain before/after compiler and analyzer controls.

Cppcheck 2.22.0 cannot fully parse the actual GCC16 C++ header context.
The same `__has_builtin` failure occurs with the Qt header-only control;
preprocessed libstdc++ input also exceeds its parser support. C header
controls reproduce the POSIX signal-handler sentinel and `vprintf`
declaration/model diagnostics. These are recorded coverage gaps and model
diagnostics, not a clean Cppcheck result. No task suppression is used.

The corrected native viewer passes Memcheck with zero errors and zero
definite, indirect or possible leaks. The positive display lifecycle and
four real refusal paths run with leak failures enabled. Qt/GLib global
caches remain reachable. Valgrind's shipped `dtv-addr-init` suppression
accounts for eight bytes; this is not a task-specific suppression.

Meson, the upstream GLib generators and upstream Cppcheck's build generator
use Python. The profile's own code uses C, C++, Ruby and shell.
Camera capture, RTSP, hardware codecs, GPU presentation, audio, a physical
operator workstation and long-duration operation require separate checks.
