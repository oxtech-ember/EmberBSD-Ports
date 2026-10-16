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
uses four actual QMediaPlayer/QVideoSink pairs in one QWidget.
The default window is 1280×800. The accepted target selection uses 640×480.
All four decoders still produce full 2048×1500 frames.
Each input is H.265, 2048×1500, 9 fps, with a different lossless I420 pattern.
Both the 36-frame and 180-frame sets pass independent native decoding,
whole-stream SHA256 comparisons and exact source-timestamp checks.
The viewer verifies every active decoded luma and chroma byte and frame ID.
An independent RFB client reads the actual displayed framebuffer.

Sink handoff is bounded to sixteen frames per stream. Overflow is counted;
strict acceptance still fails if any expected source frame is absent.
The SDR BT.709 CPU path scales decoded YUV to the viewport before RGB
conversion through the current FFmpeg `sws_scale_frame` API, with point
sampling by default and optional bilinear filtering. Dirty-quadrant repaint
and cached static labels avoid repeated full-window drawing and text shaping.
Full-resolution decoding and the independent pixel oracle remain enabled.
The accepted command also uses `--ffmpeg-cpu-count 1`. This is a public
FFmpeg hint for automatic thread-pool sizing, not a change to the four vCPUs.

The initial target run exposed unbounded queued frame retention and GUI
starvation. Both 36-frame runs decoded and verified every frame, but each
quadrant painted only twice. The 180-frame run exhausted a 2 GiB guest.
These failures motivated the bounded handoff and viewport conversion.
They are retained as failed evidence, not counted as accepted display runs.

## Installed target result

Full-system QEMU 10.0.13 runs the real EmberBSD amd64 kernel and userland
with TCG, four vCPUs and 2 GiB RAM. KVM is unavailable in this environment.
The target creates six dependency packages and the viewer package with
real `pkg_create`. It reuses seven hash-verified common runtime packages.
All fourteen install, pass `pkg_admin check`, and survive normal removal
and reinstallation. Required-package deletion is refused. The Qt package's
registered conflict metadata is also checked.

The first and reinstalled 36-frame runs each decode, verify and paint all
144 frames. The final 180-frame run does the same for all 720 frames.
There are zero missing IDs, mailbox coalescences, timestamp regressions or
decoded-pixel errors. The loaded backend is FFmpeg; frames use CPU memory.
All three target phases have independent full-coverage RFB captures with
at least two different actual window images.

The final long-run measurements use 640×480 windows and full-pixel checks:

| Execution | Wall time | Delivered fps per stream | Painted fps per stream | Process CPU | Peak RSS |
| --- | ---: | --- | --- | ---: | ---: |
| EmberBSD amd64, four-vCPU TCG | 20.430 s | 9.100–9.305 | 9.114–9.326 | 372.55% | 262.5 MiB |
| Native Linux control | 20.160 s | about 9.0 | 9.018 | 39.68% | 214.1 MiB |

One fully used core equals 100%. These process measurements include player
startup, decoding, full-pixel verification, conversion, drawing and the VNC
server. QApplication initialization precedes the measured interval.
Snapshot encoding and report serialization follow it. Guest CPU accounting
does not measure QEMU's host overhead or predict physical workstation load.
Short cold-start runs have wider frame-interval variation; they establish
package and pixel correctness, not sustained throughput.

`tests/check-report.rb` in Examples independently recomputes delivery and
paint rates from the actual CSV, checks all expected IDs and cross-checks
the JSON metrics. The long target and native runs pass an explicit 8.95 fps
minimum, the lower rounding boundary for approximately 9.0 fps.
Corrupted FPS and missing-row controls are rejected. This threshold does
not replace the measured ranges above or change the media time base.

RFB requests full snapshots once per second to bound observer traffic;
RFB sampling does not measure presentation FPS. A sampled window oracle
also accepts three unambiguous target captures from the two short runs.
It identifies all four quadrants from actual RGB pixels. Downscaled marker bits can leave ambiguous
frame IDs or channels, which it reports as failures. Full decoded-pixel
checks and CSV validation cover every frame independently of that sampling.

Larger-window and earlier unbounded/bilinear runs remain failed or slower
controls. This result does not accept 1280×800 throughput on TCG, physical
display timing, physical workstation performance or camera input.

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
