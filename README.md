# EmberBSD Ports

Source build recipes, portability patches and build probes for
[EmberBSD](https://github.com/oxtech-ember/EmberBSD).

Sources are downloaded from their original upstream locations and verified
against pinned hashes. This repository carries our recipes and patches,
with their provenance and validation limits. It does not mirror source
archives or store generated binaries.

## Purpose

Ports supplies the native dependencies used by EmberBSD applications and
examples. It owns the delta over pkgsrc: package recipes, portability patches,
source provenance, shared dependency profiles and reproducible build probes.
Kernel changes belong in EmberBSD; application demonstrations belong in
Examples. A source probe remains experimental until packaging and the intended
runtime behavior are validated.

## Current contents

- [Robotics and ROS 2](profiles/robotics/README.md): Zenoh-Pico 1.10.1
  native package and tests verified; the Examples C controller exchanges
  typed commands and telemetry with ROS 2 Jazzy, including reconnect checks.
- [Common development toolchain](profiles/development-toolchain/README.md):
  GCC 16.2.0 builds in the AArch64 VM and runs there and on physical Zero 3W,
  passing C11/C++20 threads, TLS and shared-library runtime checks. The full upstream
  suite exposes platform compatibility failures; a tested upstream backport
  repairs TSVC allocation on NetBSD. The common package MAKECONF now selects
  the prepared compiler after native-GCC bootstrap; actual pkgsrc wrapper and
  installed-consumer checks pass on Zero 3W with current MPFR/MPC/libxml2.
  The repaired nb1 package passes installed module export/import/link/run
  without a private frontend, and reversible board login/SSH and pkgsrc
  defaults select it. The [cross-compiler recipe](profiles/development-toolchain/cross/README.md)
  builds GCC16 on Apple Silicon macOS; cross-built C/C++20 consumers run on
  Zero 3W with its installed GCC16 runtime. Its installed tool-search layout
  also passes split-DWARF generation without an `objcopy` path override.
  Common Qt/LLVM rebuilding and full-image integration
  remain pending.
  [GDB 18.1nb1](profiles/development-toolchain/gdb/README.md) is cross-built and
  installed in the AArch64 VM, with split/supplementary DWARF, Unicode and
  live register/signal-unwinding checks. Its [pkgsrc recipe](profiles/development-toolchain/gdb/package.md)
  replaces `devel/gdb` and adds zstd, bounded DWARF procedure calls and
  current location-list handling. Its 72 entry-value checks cover arithmetic,
  reconstructed registers, typed float/SIMD values and unavailable history. The OS-owned
  [development image](https://github.com/oxtech-ember/EmberBSD/tree/main/ember/image)
  passes offline package installation and live split-DWARF32/64 debugging
  after a normal AArch64 VM reboot;
  the [expanded matrix](profiles/development-toolchain/gdb/dwarf-variants.md)
  records 32 format cases, 24 expression cases and 14 agent-compiler checks.
  The common [LLVM 23.1.2nb1 package](profiles/common-build-tools/cross/llvm-dwp-tests.md)
  creates and repacks mixed DWARF32/64 DWP files, including type units and
  shared indexed tables. Its installed tool passes 104 cases with live GDB
  values; existing C API, bitcode and ORC JIT consumers still pass.
- [Current common build tools](profiles/common-build-tools/README.md):
  [Mac cross packages](profiles/common-build-tools/cross/README.md) for
  pkgconf 3.0.7, GNU M4 1.4.21, Libtool 2.6.2 and
  [Binutils 2.47nb1](profiles/common-build-tools/binutils.md) pass ordinary package checks
  and installed AArch64 VM consumers with GCC16. Cross metadata, package
  replacement and rollback have regression checks. Binutils has a verified
  DWARF32/64 line-table repair; GNU tools are selected explicitly during
  acceptance, with GCC bootstrap-tool default migration still pending.
  [Python 3.14.8](profiles/common-build-tools/python.md) also cross-builds and
  passes installed C/C++ embedding, extension loading and 21 upstream suites
  on the AArch64 VM. Meson 1.12.1 and Ninja 1.13.2 cross packages pass
  installed C/C++ builds, Python embedding, incremental/error handling and
  install-RPATH checks with explicit current GNU as/ld. The profile provides
  matching LLVM/Clang/LLD 23.1.2 source
  recipes with upstream lit, scoped native Clang/GCC16 defaults, strict
  common selection and host source contracts. Focused native macro/selection
  checks cover Python, LLVM family selection and real GCC16 config metadata.
  The complete LLVM23 core package now passes normal packaging and installed
  [C API/bitcode and four ORC JITLink lifecycles](profiles/common-build-tools/cross/llvm-api-tests.md)
  on Zero 3W. Packaged upstream lit passes launcher and PASS/XFAIL/FAIL checks
  in AArch64 UTM. Mesa26 passes installed llvmpipe/ORC acceptance below;
  Clang/LLD packaging and the TinyGo consumer remain pending.
- [Common graphics source packages](profiles/common-graphics/README.md):
  canonical MesaLib 26.2.4nb2, adapted libdrm 2.4.134nb1,
  Wayland 1.26.0nb1 and wayland-protocols 1.49 compose the common
  GCC16/Python314/Meson112/shared LLVM23 profile for NetBSD 11/AArch64.
  Source, export and dependency-selection checks cover X11/Wayland,
  EGL/GBM and classic VirGL/softpipe/llvmpipe. The complete core-only libdrm
  payload cross-builds on macOS/GCC16, matches all 26 PLIST entries and passes
  upstream hash, skip-list and exported-symbol checks in AArch64 UTM.
  A [temporary Mesa26 cross diagnostic](profiles/common-graphics/cross/README.md#temporary-headless-mesa-diagnostic)
  passes software GLES shader/pixel checks and 30 upstream target test runs on
  Orange Pi Zero 3W (A733). The installed
  [Wayland package](profiles/common-graphics/cross/wayland.md) passes all 26
  enabled upstream invocations there after the paired kernel IPC repairs.
  The full [Mesa package](profiles/common-graphics/cross/mesa-package.md) now
  installs normally and passes four llvmpipe/LLVM23 EGL pixel lifecycles and
  all 37 upstream invocations on Zero 3W; one internal case skips and nine
  NIR cases remain disabled. The nb2 XCB pkg-config correction preserves
  byte-identical Mesa libraries. Installed [libepoxy](profiles/common-graphics/cross/epoxy.md)
  passes real dispatch through those providers and four pure upstream tests.
  After the common [LLVM23.1.2nb1 revision update](profiles/common-graphics/cross/mesa-runtime-rebind.md),
  fresh Mesa and libepoxy rendering checks pass on Zero 3W; the earlier
  37-test result is retained separately.
  The same Mesa/LLVM providers pass [GBM/PRIME/EGLImage pixel interchange](profiles/common-graphics/cross/gbm.md)
  through native VirtGPU buffers in an isolated AArch64 VM, with verified
  live libraries and explicit llvmpipe rendering.
  [wlroots 0.20.2nb4](profiles/common-graphics/cross/wlroots-package.md) now
  uses this same stack for GLES2 rendering, KMS framebuffer import and
  headless presentation. Four root and four unprivileged lifecycles pass
  all 1024 pixels and preserve renderer buffers after caller GEM_CLOSE.
  Its [DRM/input package](profiles/common-graphics/cross/drm-input.md) also
  presents four verified frames at 1280x800 through a real libseat session
  and enumerates two wscons input devices. All 131 selected dependency checks
  pass in the VM. The same package also passes four [VirGL DRM frames](profiles/common-graphics/cross/wlroots-virgl.md)
  on the paired Metal host. Input events, VT switching, application surfaces
  and a complete accelerated desktop remain unverified.
  A separate [guest VirGL check](profiles/common-graphics/cross/virgl-draw.md)
  passes four offscreen GLES lifecycles with this same Mesa/LLVM package
  stack and the paired ANGLE Metal host on Apple M3.
  Current [text and image dependencies](profiles/common-graphics/cross/labwc-dependencies.md),
  including GLib 2.90.1, Pango 1.58.2, HarfBuzz 14.6.0 and Cairo 1.18.6,
  cross-build with normal package checks. Four installed AArch64 VM cycles
  pass real font selection, text shaping, CPU rasterization and PNG roundtrip,
  with causal negative controls. Installed [desktop support](profiles/common-graphics/cross/desktop-support.md)
  also passes all four libsfdo 0.1.4 upstream tests and a private D-Bus 1.16.2
  session with name ownership, real method replies and error/lifecycle checks.
  A [Rust 1.99 std-only cross probe](probes/rust-cross-std/README.md) passes
  threads, TLS destructors, unwinding and C-library consumers in AArch64 VM.
  The [shared Rust host recipe and cargo-c](profiles/common-build-tools/rust.md)
  pass macOS installation and native C ABI checks after a Mach-O packaging repair.
  Their [normally installed EmberBSD target std](profiles/common-build-tools/rust-target-std.md)
  also passes those target lifecycles and a Cargo consumer with host proc macros.
  The [full GI package](profiles/common-graphics/cross/introspection.md) cross-builds
  with real GType discovery and upstream hash/search checks on EmberBSD/CM5.
  Matching GLib 2.90.1 metadata now cross-builds all seven GIR/typelib pairs
  and passes target loading and introspection/libffi invocation on CM5.
  Current [GdkPixbuf and shared MIME packages](profiles/common-graphics/cross/gdk-pixbuf.md)
  preserve all thirteen raster formats, metadata and thumbnailer payload.
  Four CM5 cycles pass complete and incremental decoding with pixel checks.
  The [sysroot rules](profiles/common-build-tools/cross/sysroot.md) preserve
  fork libc provenance and reject divergent shared-library aliases.
  The [librsvg 2.63.2 consumer](profiles/common-graphics/cross/librsvg.md)
  passes four CM5 CPU cycles with SVG/PNG pixels, dynamic loading, AVIF,
  text and typelib invocation. Its corrected isolated bundle includes
  verified MIME data; this SVG result is CPU rendering.
  The [labwc 0.20.2nb2 package](profiles/common-graphics/cross/labwc.md) now
  cross-builds with SVG, icons, translations and man pages. Its 62 installed
  payload files/links and 80 target ELF files pass inspection.
  Its [VirGL session check](profiles/common-graphics/cross/labwc-session.md)
  passes two sessions on Apple M4/ANGLE Metal: 66 captured EGL frames each,
  real virtual USB input, keyboard-driven window/maximize/restore/fullscreen
  transitions, mouse dragging and clean restart. This does not
  qualify sustained desktop use or physical-board GPU acceleration.

- [Current robotics libraries](probes/robotics-foundations/README.md): native
  OpenCV 5.0.0, Eigen 5.0.1 and gpsd 3.27.5 source probes; installed vision,
  numerical and synthetic GNSS workflows verified on AArch64.
- [Signal processing and IMU estimation](probes/dsp/README.md): liquid-dsp 1.8.3,
  FFTW 3.3.11, VOLK 3.3.0 and Fusion 1.3.3 pass 19 installed AArch64 VM cases.
  They cover filtering, resampling, QPSK, spectra, generic/NEON vector kernels
  and synthetic orientation/bias estimation. Ports preserves the common FFTW,
  source adaptations and pkgsrc patch origins; physical SDR and IMU are unverified.
- [Software radio flowgraphs](probes/gnuradio/README.md): GNU Radio 3.10.12.0
  reuses common FFTW/VOLK/fmt and passes three installed AArch64 VM contracts.
  The [standalone BPSK example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/gnuradio-channel)
  recovers 2,048 payload bits through a noisy software channel and measures
  the expected errors without carrier correction. No physical SDR or GUI is required.
- [Offline visual SLAM](probes/orb-slam3/README.md): ORB-SLAM3 v1.0 uses common
  Eigen 5.0.1/OpenCV 5.0.0 through a headless adaptation with worker shutdown,
  cancellation and missing-pose export regressions. Eight installed AArch64 VM
  cases pass. The [RGB-D example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/orb-slam3-rgbd)
  tracks 573 TUM fr1/desk pairs with 1.71–1.76 cm translation ATE RMSE in two
  controlled runs. Cameras, IMU fusion, boards and sustained operation are unverified.
- [Navigation source profiles](probes/gtsam/README.md): GTSAM 4.3.0,
  [PCL 1.15.1](probes/pcl/README.md), [OpenVINS 2.7](probes/openvins/README.md)
  and [RTAB-Map 0.23.8](probes/rtabmap/README.md) have pinned recipes and numerical
  consumer checks. They share current Eigen/OpenCV dependencies; native
  installation and these navigation scenarios remain unverified.
- [Local trajectory generation](probes/ruckig/README.md),
  [quadratic optimization](probes/osqp/README.md) and
  [motion planning](probes/ompl/README.md): Ruckig 0.19.4 and OSQP 1.0.0 pass
  installed macOS software contracts; OMPL 2.0.2 has a prepared source profile
  and checked geometry oracle. Native EmberBSD validation remains pending.
- [Ethernet SDR source profile](probes/sdr/README.md): SoapySDR 0.8.1,
  libiio 1.0.0, libad9361-iio and SoapyPlutoSDR use a common
  [libxml2 2.15.4 provider](probes/libxml2/README.md). Installed macOS contracts
  cover synthetic IQ, separate contexts, RX errors and loopback transport.
  Native EmberBSD, physical PlutoSky/AD9361 RX and per-call stream deadlines
  remain unverified; the profile includes instructions for continuing on hardware.
- [Robotics and automotive developer tools](probes/robotics-tools/README.md):
  MCAP C++ 2.1.3, AprilTag 3.4.5, dbcppp 3.2.6, iso14229 0.11.0,
  Ceres 2.2.0, BehaviorTree.CPP 4.9.0 and libmodbus 3.2.0 source profiles.
  They provide recording/replay, marker pose, DBC decoding, UDS over ISO-TP,
  nonlinear fitting, asynchronous behavior trees and Modbus TCP/RTU.
  All seven pass 19 installed application cases in an AArch64 VM, including
  error paths. Physical camera, CAN/RS-485, ECU and PLC workflows are unverified.
- [Media and OpenCV videoio](probes/media/README.md): FFmpeg 9.0.2,
  GStreamer 1.28.7 and OpenCV 5.0.0 pass installed file/video pipeline checks
  on AArch64, including both videoio backends, timestamps, seeking, lossless
  output and malformed input. Camera capture and acceleration are unverified.
- [MQTT smart-home foundation](probes/mosquitto/README.md): Mosquitto 2.1.2
  builds with common GCC 16.2, cJSON 1.7.19 and SQLite 3.53.4. Twelve installed
  AArch64 VM cases pass MQTT 3.1.1/5 QoS 0/1/2, authentication/ACL, verified
  TLS and retained-state recovery. Packaging, boot service and other
  smart-home ports remain pending.
- [Network diagnostics kit](profiles/network-diagnostics/README.md):
  cross-built CLI capture, analysis and load tools for boards. libpcap
  1.10.7, tcpdump 4.99.6 and iperf3 3.21 install from binary packages on
  Raspberry Pi 5; tcpdump captured live Wi-Fi traffic through BPF without
  kernel drops, and iperf3 measured TCP, reverse TCP and zero-loss UDP
  jitter against a LAN peer. The Wireshark 4.6.8 CLI kit (dumpcap, tshark,
  capinfos, editcap, mergecap) cross-builds with Qt, Lua, HTTP/3 and docs
  disabled; on the board dumpcap passed a three-file ring-buffer capture
  under load and tshark read pcap, pcapng and BTSnoop traces. The native
  `hcisnoop` recorder writes BTSnoop traces from the netbt HCI socket tap
  that Wireshark reads as "Bluetooth HCI H4"; it captured a real controller
  inquiry with correct directions. Wi-Fi monitor mode, Lua dissectors and
  the GUI remain separate queue items.
- [Local AI CPU packages](profiles/ai-cpu/README.md): pkgsrc recipes for
  llama.cpp 0.6.0 and whisper.cpp 1.9.4; native ARM64 package installation,
  text generation, WAV transcription, and loopback HTTP inference verified.
- [CPU inference and audio](probes/ai-engines/README.md): ONNX Runtime 1.30.0,
  ncnn 20260526, RNNoise 0.2 and Silero VAD 6.2.3 pass seven native installed
  consumer checks on AArch64. They cover numerical inference, stream state,
  speech/silence and invalid inputs; explicit ORT worker affinity is checked
  separately. These are source probes, without microphone or accelerator validation.
- [LiteRT and LiteRT-LM](probes/litert/README.md): LiteRT 2.2.0 provides a
  shared C/C++ CPU runtime for `.tflite` models; LiteRT-LM 0.18.0 adds a
  SentencePiece language-model engine. The macOS-to-AArch64 source profile
  passes installed C/C++ numerical/error contracts and real TinyLlama text
  generation on a physical A733 board. Explicit metadata preparation preserves
  the model's weights and tokenizer. These are source builds, without GPU/NPU
  validation; the profile records memory use and model limits.
- [A733 accelerator audit](probes/a733-accelerators/README.md): compiled vendor
  and Mesa feature tables identify the VIP9000 NPU's missing TP path and MMU
  differences. Exact PowerVR firmware is pinned. The Zero 3W FDT and device
  checks confirm that native accelerator drivers are not attached yet.
- [Compass NPU UMD source contracts](probes/compass-umd/README.md): pinned
  upstream descriptor-zero and failure-cleanup fixes pass host/native software
  contracts; public core-count bounds pass 58 native production-extracted cases
  on AArch64/GCC 16.2, with legacy behavior preserved. The complete 27-source
  UMD cross-build and 85 actual no-device API checks also pass on A733.
  Kernel/DMA integration and model execution remain unverified.
- [SQLite and local document retrieval](probes/sqlite/README.md): SQLite 3.53.4
  installed C consumers pass FTS5/JSON, transactions, concurrent readers and
  process-crash/reopen checks. A C application retrieves local documents and
  validates quotations from the existing llama.cpp CPU server on AArch64.
- [Native Wayland and VirGL build probe](probes/wayland-utm/README.md): pinned
  current Mesa 26.2.4 source adaptation with DSO-lifetime and numeric
  regressions, paired libdrm, wlroots and labwc recipes. Mesa26 headless
  softpipe tests now pass on A733; earlier Mesa21 native KMS/input checks
  remain separate. The installed common Mesa/LLVM package now passes CPU
  rendering, guest VirGL offscreen and DRM presentation acceptance above.
- [UTM VirGL host source adaptations](probes/utm-virgl-host/README.md): the
  accepted upstream size-truncation fix is prepared for UTM's pinned 1.3.0
  renderer. Actual-source macOS/arm64 checks show compiled BASE RED and
  patched GREEN across 23 cases, including ASan/UBSan. Local CREATE patches
  also prevent publication after reported renderer failures and unwind owned
  partial allocations; actual-function macOS/arm64 and sanitizer checks pass.
  A [classic backing ledger](probes/utm-virgl-host/BACKING.md) keeps guest
  mappings alive through renderer detach and every cleanup path, including
  deferred UNREF. Causal ownership checks also pass with `NDEBUG`.
  An opt-in [classic lifecycle barrier](probes/utm-virgl-host/LIFECYCLE.md)
  stops CPU producers before reset/fault revocation and detaches every backing
  before releasing any mapping. Source tests cover display-blocked command
  handoff, query polling and deferred native cleanup.
  [Reported command and fence errors](probes/utm-virgl-host/COMPLETION.md)
  enter that barrier before any failed command can receive success; 683
  source assertions pass in plain, sanitizer and NDEBUG runs.
  [Checked GL/EGL waits](probes/utm-virgl-host/wait-errors.md) distinguish
  pending, signaled and failed fences. Paired renderer/QEMU source checks
  preserve ownership through a failed poll and reject the old host ABI.
  The [full renderer recipe](probes/utm-virgl-host/host/README.md) builds and
  links with current libepoxy 1.5.10 on macOS. Direct Apple M3 acceptance
  passes texture readback, decoded framebuffer clears, shader triangle pixels,
  real fences and three
  cleanup/reinit cycles; a
  reproduced null-context cleanup failure is fixed. Truncated command payloads
  also return EINVAL instead of false success, verified through the full native
  decoder with valid-command controls. Reported surface/GL errors also reject
  classic submissions and poisoned contexts, with native checks both with and
  without upstream GL error checking. [Query results](probes/utm-virgl-host/host/query-results.md)
  reject incomplete backing and preserve delayed errors/fence ownership;
  native Metal and causal sanitizer contracts pass. A separate
  [native reset test](probes/utm-virgl-host/host/native-reset.md) passes three
  live-resource resets, cancelled-fence checks and shader rendering after
  ID reuse. This does not establish interruption of running GPU work or a
  guest 3D reset. The [full paired QEMU
  recipe](probes/utm-virgl-host/qemu/README.md) also builds and passes an isolated
  2D guest boot on ANGLE Metal, including libdrm and 32 GEM/PRIME lifetimes.
  Three [real QMP resets](probes/utm-virgl-host/qemu/reset.md) with a live guest
  2D GEM resource also pass, including four Metal renderer initializations.
  The [Cocoa context repair](probes/utm-virgl-host/qemu/cocoa-context.md) additionally
  enables the installed guest's four-frame VirGL DRM check on Metal. In-flight
  3D reset/display lifetimes and a complete accelerated session remain
  unverified. The host profile defaults to OFF; only the separate EMBERVIRGL
  kernel explicitly requests guest VirGL.
- [Native Phosh session](probes/phosh/README.md): Phosh 0.58.0 builds and
  runs inside GNOME/X11 through Phoc and software-rendered Wayland.
  Stevia screen-keyboard input in English/Russian, a saved text document
  and the patched GTK4 Demo were verified.
- [Current Plasma Mobile](probes/plasma-mobile/README.md): Plasma Mobile
  6.7.5 builds and installs on the AArch64 VM; KWin displays a real Qt Wayland
  window with keyboard input. Activities activation and the upstream
  application menu are checked. The complete mobile workflow still needs
  the common OpenGL stack and an enabled KWin shortcut backend.
  [Qt 6.12/KF6.30 source recipes](probes/plasma-mobile/toolkit/README.md)
  and the [shared FFmpeg9 recipe](profiles/common-media/README.md) pass
  source/export checks. Native audio API/registration and host metadata
  extraction checks pass; the native package migration remains pending.

- [Openbox](probes/openbox/README.md) and
  [Enlightenment](probes/enlightenment/README.md): Openbox 3.6.1 and
  Enlightenment 0.27.1/EFL 1.28.1 pass native software X11 window management,
  keyboard input through XTEST, text editing/saving and session exit.
  The [shared launcher and runtime test](probes/x11-desktops/README.md)
  retain the user's HOME and isolate session configuration and processes.
- [awesomeWM](probes/awesome/README.md): the 4.3 source probe uses LGI 0.9.2
  with the common system Lua. Native build, LGI/icon regressions and the
  same X11 window/input/save/exit workflow pass. Patches correct startup
  pthread linkage, Lua 5.4 version reporting and the WM selection name.
- [Xfce](probes/xfce/README.md): pinned 4.20 components, libwnck 43.3 and
  Mousepad 0.7.0 build and run in an isolated NetBSD 11/AArch64 UTM session.
  [Native checks](probes/xfce/VALIDATION.md) cover Thunar navigation,
  Mousepad save/reopen/edit, menu application launch, X11 window/input
  behavior and clean exit. Hardware input and GPU acceleration are unverified.

The graphical entries remain experimental probes,
not installable packages or phone images. Each recipe records its tested
runtime and platform boundaries.
Helpers stop on errors and keep output in private user directories.

## Package integration

The preferred foundation for package recipes is
[pkgsrc](https://www.netbsd.org/docs/pkgsrc/components.html), already used
by EmberBSD's NetBSD-derived package environment. It provides upstream
fetching, checksums, patches, dependency handling and binary packaging.
This repository does not implement another package manager.

`upstream/pkgsrc` pins the pkgsrc-2026Q3 base as a Git submodule. Local recipes
under `pkgsrc/` use ordinary `Makefile`, `distinfo`, `DESCR`, and `PLIST` files.
`scripts/prepare-pkgsrc.sh` exports that pinned base and adds the local recipes
to an independent working tree. Experimental probes remain under `probes/`
until their package integration and runtime are validated. No signed binary
package repository is provided yet.

## Contributions and provenance

All repository material is written in English. Record the upstream
version, URL, archive hashes, license and origin of each patch. Preserve
upstream copyright and SPDX notices. State whether patches are local,
submitted upstream or accepted upstream; AI assistance is not concealed.

Distinguish a configured project, a compiled library, passing tests and
a working application. Keep logs and downloaded artifacts outside Git.
Examples that use these ports belong in
[EmberBSD Examples](https://github.com/oxtech-ember/EmberBSD-Examples).

## Related EmberBSD projects

[EmberBSD](https://github.com/oxtech-ember/EmberBSD#emberbsd-ecosystem) is the
central project and the entry point for the ecosystem.

- [EmberBSD](https://github.com/oxtech-ember/EmberBSD) — OS, drivers, boards and system builds.
- [EmberBSD-Examples](https://github.com/oxtech-ember/EmberBSD-Examples) — standalone demonstrations using these dependencies.
- [EmberBSD-Runtime](https://github.com/oxtech-ember/EmberBSD-Runtime) — application execution and device operations; design stage.
- [EmberBSD-SDK](https://github.com/oxtech-ember/EmberBSD-SDK) — application contracts and development tools; design stage.
- [Ember-Agent-Skills](https://github.com/oxtech-ember/Ember-Agent-Skills) — instructions for AI coding assistants, ports and tested contributions.

## Connect developer skills

[Ember-Agent-Skills](https://github.com/oxtech-ember/Ember-Agent-Skills#use-in-your-development-environment)
provides portable Agent Skills packaged with Agent Plugins. Use the installation
method supported by your development environment. Codex is one verified host.

Use a Codex CLI with plugin support:

```sh
codex plugin marketplace add oxtech-ember/Ember-Agent-Skills --ref main
codex plugin add emberbsd-development@ember-agent-skills
```

Start a new conversation and ask `$emberbsd-repository-guide` to prepare a
port, run the appropriate checks and open a tested contribution. Follow the
[installation, verification and update guide](https://github.com/oxtech-ember/Ember-Agent-Skills#use-in-your-development-environment)
for the complete procedure and other assistant environments.
