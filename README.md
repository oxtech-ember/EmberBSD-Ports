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

- [Common libspnav 1.2](profiles/common-graphics/cross/libspnav.md): full
  native/AArch64 GCC16 packages retain Unix and X11/Magellan interfaces.
  Real native socket lifecycles pass strict memory checks after causal queue
  and descriptor-zero repairs. Installed EmberBSD clients pass five socket
  contracts under an ordinary user, plus package removal and reinstallation.
  Physical input and X11 display acceptance remain pending.
- [Common SWIG 4.5.1](profiles/common-build-tools/cross/swig.md): the full
  native GCC16 package verifies all 846 files and the upstream Python 3.15
  example. A causal CCache repair preserves compiler fallback with closed
  stderr. Strict memory findings, target packaging and KiCad bindings remain
  separate acceptance work.
- [KiCad application source](probes/kicad/application/README.md): the complete
  10.0.7 source keeps QA and IPC. GCC16 causal checks repair NetBSD context,
  loader and DXF platform selection. The bundled context implementation passes
  3,003 exchanges in the AArch64 VM and strict native Memcheck. The actual
  API library and version-message consumer pass native memory checks and
  AArch64 execution. Full KiCad configuration, package and CAD workflows
  remain pending.
- [KiCad OCCT source](probes/kicad/occt/README.md): OCCT 8.0.1 retains
  NetBSD locale, path and exception support. GCC16 target compilation and
  focused native regressions cover the source repairs; KiCad uses the
  current exception API. The complete OCCT package and installed STEP
  geometry checks remain pending.
- [Common Eigen 5.0.1](profiles/common-graphics/cross/eigen.md): the existing
  provider retains its CMake/header interfaces and full companion libraries.
  GCC16 AArch64 packaging verifies all 613 entries; four selected native
  and installed EmberBSD numerical checks pass. Normal package removal and
  reinstallation preserve the verified ownership boundary.
- [JBIG-KIT 2.2nb1](profiles/common-graphics/cross/jbigkit.md): the common provider
  keeps both libraries and all four image tools. Ordinary GCC16 native and
  AArch64 packages pass package checks; native upstream tests and installed
  library memory checks pass. Fourteen installed CLI memory/image cases also pass.
  Target execution and TIFF integration remain pending.
- [wxWidgets and WebKit sources](profiles/common-graphics/cross/wxwebkit.md):
  stable wxWidgets 3.2.12 and paired WebKitGTK 2.54.1 recipes retain WebView,
  media and OpenGL. Native generator routing, actual GCC16 target link checks
  and focused native Skia memory checks pass. The rebuilt Skia locale contract
  passes in EmberBSD with installed GCC16 runtime nb3. Full WebKit packages
  and GUI integration remain pending.
- [Maintained FreeImage sources](profiles/common-graphics/cross/freeimage.md):
  FreeImage/FreeImagePlus 3.19.25 and LibRaw 0.22.2 retain common codecs for
  OCCT. Source and focused native half checks pass; complete packages and
  installed image workflows remain pending.
- [RapidJSON with GCC16](profiles/common-graphics/cross/rapidjson.md): the common
  current snapshot retains its header APIs, examples and strict unit/performance
  builds. Source repairs cover external pointer tokens and shared pool ownership.
  Ordinary native/AArch64 packages, 471 native unit tests and strict Memcheck
  pass. Installed target execution remains pending.
- [OpenEXR and OpenJPH](profiles/common-graphics/cross/openexr.md): current
  3.5.2 and 0.32.0 providers retain shared libraries, tools and system codecs.
  Ordinary GCC16 native/AArch64 packages pass static payload checks. Native
  image round trips, focused strict memory checks and all 147 OpenEXR tests
  pass. Target codec/API checks and normal package removal/reinstallation pass.
- [KiCad protobuf prerequisites](probes/kicad/protobuf/README.md): protobuf
  36.2 and Abseil 20260817.0 build with native GCC16 and shared zlib 1.3.2.
  Four allocation-failure controls reproduce upstream UPB defects and pass
  after repair. The installed C++ API passes fourteen checks, including gzip.
  Matching code generation retains its output and error behavior. Documented
  process-lifetime exceptions keep the original CLI's memory failures visible.
  The same C++ and UPB contracts pass in the AArch64 E34 guest with the
  GCC16-built shared-library closure. The ordinary runtime package also passes
  both contracts, all payload checks and normal removal/reinstallation.
  Complete KiCad integration remains pending.
  The [common Abseil recipe](profiles/common-build-tools/cross/protobuf.md)
  repairs NetBSD stack traces. Its ordinary AArch64 package passes two installed
  SDK consumers, all 816 payload checks and removal/reinstallation.
  Cross protobuf recipes separate runtime libraries from target generators and
  SDK files. Their source ownership checks preserve the full native package.
  Both packages pass normal checks, all 353 installed SDK payload entries and
  two GCC16 consumer links. Actual KiCad API generation preserves all schema
  bytes; its scoped system-macro repair passes native and target contracts.
  Common CMake discovery now prefers selected package dependencies over base
  namesakes; GCC16 zlib discovery/link controls preserve native behavior.
- [KiCad SPICE prerequisites](probes/kicad/ngspice/README.md): ngspice 47
  source repairs retain the shared C API, XSPICE, OpenMP, FFTW and Readline.
  Native numerical and causal ownership checks pass. Raw memory reports
  retain process-lifetime allocations. Ordinary GCC16 AArch64 packages pass
  installed API18, CLI, the KiCad-exported divider, OpenMP worker activation
  and removal/reinstallation checks. A separate GCC16 target regression repairs
  the configure-time memory-query selection; revision-1 package acceptance
  and complete KiCad application execution remain pending.
  The common [Libtool runtime-path repair](profiles/common-build-tools/cross/libtool-runtime-paths.md)
  passes a real GCC16 C++ library regression for target RPATH and `.la` metadata.
- [FFTW and terminal dependencies](profiles/common-build-tools/cross/README.md#installed-fftw-readline-and-ncurses):
  ordinary GCC16 packages pass AArch64 VM Fourier, Readline input/history,
  PTY editing and removal/reinstallation checks. FFTW covers double/float
  with pthread/OpenMP. Installed ncurses terminfo files and aliases match
  the package and SDK. Libtool metadata portability and full KiCad integration
  remain pending.
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
  Relocated amd64 binutils also retain 67 default linker scripts and pass
  a real secondary-emulation standalone link; OS boot remains separate.
  The recipe's `--kernel` mode prepares frontends without a userland sysroot;
  application mode retains target headers/runtime. The Linux GCC16 path also
  builds the full kernel, four modules, and three DTBs; all portable contracts
  and artifact checksums pass. See the [OS build evidence](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/cross-build.md#linux-gcc16).
  Boot acceptance remains separate.
  The explicit amd64 target selects x86_64 tools and runtime paths; host
  target-selection regressions pass. The runtime bootstrap and
  [runtime-only package](profiles/development-toolchain/runtime/README.md)
  keep compilers out of application images. Host package creation and isolated
  installation pass for synthetic amd64 and AArch64 runtime fixtures with
  native pkgtools. Target triplet, ELF and package architecture must agree.
  A [fresh libstdc++ helper](profiles/development-toolchain/bootstrap/libstdcxx.md)
  builds the NetBSD locale repair with explicit inherited-component checks
  and retains all 6,190 defined dynamic symbol identities.
  The [RELRO relink](profiles/development-toolchain/bootstrap/relro.md) reproduces
  three original AArch64 runtime DSOs byte-for-byte, then passes ABI and stock
  RELRO checks. The ordinary AArch64 nb3 package passes all pkgsrc gates,
  coordinated SDK migration and an installed upgrade in the verified E34 VM.
  Plain/LTO thread, TLS, OpenMP and large atomic checks pass, together with
  C11/C++20 DSO exceptions. The nb3 removal/reinstallation check remains pending.
  The [NetBSD C++ locale repair](profiles/development-toolchain/locale.md)
  preserves configured numeric conversion behavior without changing the process
  locale. Installed plain/LTO locale workers and the rebuilt Skia contract pass.
  Desktop and amd64 runtime execution, common Qt rebuilding and full-image
  integration remain separate checks.
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
- [attr 2.6.0](probes/plasma-mobile/toolkit/tests/attr/README.md): complete cross
  package, retained libattr ABI and corrected public headers/manual aliases.
  The installed package passes libattr, recursive CLI and nofollow checks on a
  separate CM5 FFS2ea fixture after the OS listxattr fix. Other filesystems
  require their own extended-attribute support.
- [Current common build tools](profiles/common-build-tools/README.md):
  [Mac cross packages](profiles/common-build-tools/cross/README.md) for
  pkgconf 3.0.7, GNU M4 1.4.21, Libtool 2.6.2 and
  [Binutils 2.47nb1](profiles/common-build-tools/binutils.md) pass ordinary package checks
  and installed AArch64 VM consumers with GCC16. Cross metadata, package
  replacement and rollback have regression checks. The
  [pkg-config sysroot check](profiles/common-build-tools/cross/pkgconfig.md)
  verifies actual GCC16/CMake target links and unchanged native discovery. The
  [host cross-Libtool dispatcher](profiles/common-build-tools/libtool.md)
  now selects its target configuration; its nb1 package and installed checks pass.
  Linux native-generator checks also retain the GCC16 host compiler and
  binutils under the target wrapper PATH, including ncurses' actual probe.
  The RELRO regression still rejects unprotected target ELF libraries.
  [Gettext 1.0 localization checks](profiles/common-build-tools/tests/gettext-runtime/README.md)
  pass 27 installed CM5 cases, including the Fcitx translation function.
  The autopoint archive test explicitly skips without target Autoconf.
  Binutils has a verified
  DWARF32/64 line-table repair; GNU tools are selected explicitly during
  acceptance, with GCC bootstrap-tool default migration still pending.
  [Python 3.15 host preparation](profiles/common-build-tools/python.md) now
  fixes GCC16 constant-expression use and verifies Linux pkgsrc loader naming.
  Selected native suites pass; target 3.15 execution remains pending.
  [Python 3.14.8](profiles/common-build-tools/python.md) also cross-builds and
  passes installed C/C++ embedding, extension loading and 21 upstream suites
  on the AArch64 VM. Meson 1.12.1 and Ninja 1.13.2 cross packages pass
  installed C/C++ builds, Python embedding, incremental/error handling and
  install-RPATH checks with explicit current GNU as/ld. The profile provides
  matching LLVM/Clang/LLD 23.1.3 source
  recipes with upstream lit, scoped native Clang/GCC16 defaults, strict
  common selection and host source contracts. Focused native macro/selection
  checks cover Python, LLVM family selection and real GCC16 config metadata.
  Upstream lit selects the common Python315 provider in native and cross recipes;
  host launcher PASS/XFAIL/FAIL checks pass, while target package acceptance remains separate.
  The complete LLVM23 core package now passes normal packaging and installed
  [C API/bitcode and four ORC JITLink lifecycles](profiles/common-build-tools/cross/llvm-api-tests.md)
  on Zero 3W. Packaged upstream lit passes launcher and PASS/XFAIL/FAIL checks
  in AArch64 UTM. Mesa26 passes installed llvmpipe/ORC acceptance below;
  Full LLVM/Clang/LLD 23.1.3 cross packages pass normal staging checks; LLVM core API/JIT and renewed Mesa acceptance pass on CM5. Installed Clang/LLD execution and the TinyGo consumer remain pending.
  [Linux metadata-helper preparation](profiles/common-graphics/cross/llvm-config.md)
  retains the exact native GCC16 ELF loader and runtime closure. Native
  relocation and refusal checks pass; the complete Linux LLVM helper and
  target-query agreement remain pending.
- [Common graphics source packages](profiles/common-graphics/README.md):
  [libudev-bsd render-node discovery](profiles/common-graphics/cross/libudev-render-nodes.md)
  repairs DRM classification for KWin 6.8 with a real-source regression.
  [Native DRM change events](profiles/common-graphics/cross/libudev-drm-change.md)
  preserve the ndevd wire format and pass the KWin `drm_minor` filter in source contracts.
  Native CM5 contracts also pass through a real `SOCK_SEQPACKET` pair.
  Three negative controls reproduce the old parser, filter and record-size failures.
  Live daemon delivery, HDMI hotplug and the compositor remain separate checks.
  A [bounded V3D allocation trace](profiles/common-graphics/cross/v3d-bo-trace.md) supports KWin diagnostics.
  A [fixed-size BO probe](profiles/common-graphics/cross/v3d-bo-alloc.md) checks allocation and release without GPU submission.
  MesaLib 26.2.4nb8 passes installed V3D shader rejection, triangle pixels,
  four EGL lifecycles and all 39 upstream invocations on CM5 with LLVM 23.1.3.
  One internal case skips; nine NIR cases remain disabled.
  The [BO cache mutex repair](profiles/common-graphics/tests/mesa-v3d-cache-mutex/README.md)
  initializes the missing mutex and unwinds creation failures.
  Normal installation verifies all 100 payload entries. The unchanged
  libgallium consumer passes after LLD 23 linking with preserved symbol versions.
  The [Desktop probe](probes/plasma-mobile/toolkit/tests/plasma-desktop/README.md) passes on physical CM5 with V3D and a virtual Wayland output.
  It verifies visible containment pixels, six layout checks over 30 seconds and normal shell exit.
  The unknown-output control rejects the invalid output without creating an image.
  The complete virtual session passes the CM5 checks below. Graphical login, physical HDMI and hotplug remain unaccepted.
  Adapted libdrm 2.4.134nb2, Wayland 1.26.0nb1 and wayland-protocols 1.49
  compose the common GCC16/Python315/Meson112/shared LLVM23 profile for EmberBSD/AArch64.
  An optional [PowerVR ICD](profiles/common-graphics/cross/powervr.md) retains
  these providers and adds receipt-checked native Mesa generators. On Zero 3W,
  the installed nb5 package passes four native Vulkan enumeration lifecycles,
  four llvmpipe EGL/pixel cycles and 38 upstream invocations. The same nb5
  package passes three native compute cycles on the accepted Zero 3W kernel.
  [Offscreen graphics](profiles/common-graphics/cross/powervr-offscreen.md)
  and accelerated Plasma remain separate steps for A733.
  Source, export and dependency-selection checks cover X11/Wayland,
  EGL/GBM and V3D/VirGL/softpipe/llvmpipe. The complete core-only libdrm
  payload cross-builds on macOS/GCC16, matches all 26 PLIST entries and passes
  upstream hash, skip-list and exported-symbol checks in AArch64 UTM.
  Cross Wayland recipes now separate runtime libraries from scanner/SDK files.
  Real package metadata and complete-stage partition checks preserve the native
  package. Normal AArch64 runtime/SDK packages verify all 13/23 entries; the
  installed runtime passes 24 upstream ELF invocations before and after normal
  deletion/reinstallation. Native scanner and target symbol checks pass separately.
  The installed [Wayland package](profiles/common-graphics/cross/wayland.md)
  passes all 26 enabled upstream invocations on Zero 3W.
  The full [Mesa package](profiles/common-graphics/cross/mesa-package.md) now
  installs normally and passes four llvmpipe/LLVM23 EGL pixel lifecycles and
  all 37 upstream invocations on Zero 3W; one internal case skips and nine
  NIR cases remain disabled. The [LLVM23.1.3 provider](profiles/common-graphics/cross/mesa-llvm2313.md)
  supports both V3D and llvmpipe; current CM5 nb8 acceptance is described above.
  Same-device PRIME and EGLImage also pass on CM5 after OS lifetime repairs.
  Physical HDMI, hotplug and long-duration Plasma stability remain unaccepted.
  The nb2 XCB pkg-config correction preserves
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
  Its revision-6 native GCC16 package verifies all 180 entries and passes all
  64 upstream Meson invocations with current setuptools test interception.
  Temporary hash-key leaks are repaired; target revision-6 acceptance remains pending.
  Matching GLib 2.90.1 metadata now cross-builds all seven GIR/typelib pairs
  and passes target loading and introspection/libffi invocation on CM5.
  Current [GdkPixbuf and shared MIME packages](profiles/common-graphics/cross/gdk-pixbuf.md)
  preserve all thirteen raster formats, metadata and thumbnailer payload.
  Four CM5 cycles pass complete and incremental decoding with pixel checks.
  The [sysroot rules](profiles/common-build-tools/cross/sysroot.md) preserve
  fork libc provenance and reject divergent shared-library aliases. The
  pinned-manifest importer verifies OS-owned AArch64 base/comp releases and
  extracts an isolated sysroot for external CI. Compiler packages are separate.
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
- [Factor-graph optimization](probes/gtsam/README.md): GTSAM 4.3.0 now has a
  GCC16 cross package using common Eigen 5.0.1. Installed AArch64 QEMU checks
  pass independently known linear/Pose2 solutions, covariance, errors, eleven
  upstream programs and package removal/reinstallation. The
  [CSV graph example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/gtsam-graph)
  uses the shared library. [PCL 1.15.1](probes/pcl/README.md) has GCC16 cross
  packaging with common Eigen/Boost. Installed AArch64 QEMU checks pass known
  voxel centroids, ICP motion, independent CSV, twelve upstream programs and
  all eight package lifecycles. The [point-cloud example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/pcl-cloud)
  uses the shared libraries. The expanded thirteen-library PCL profile adds
  MLS surface normals and plane segmentation; fourteen upstream programs pass
  175 tests in the recorded-map package acceptance. [OpenVINS 2.7](probes/openvins/README.md)
  retains a prepared source profile and still needs its navigation acceptance.
- [Recorded RGB-D mapping](probes/rtabmap/README.md): RTAB-Map 0.23.8 has a
  GCC16 cross package with common OpenCV 5.0.0, PCL 1.15.1nb1, GTSAM 4.3.0
  and SQLite 3.54.0. The [recorded-map example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/rtabmap-recorded-map)
  maps twelve TUM RGB-D frames with supplied recorded poses, closes and reopens
  SQLite storage, and exports 10,859 independently checked colored points.
  Installed EmberBSD AArch64 QEMU checks include fourteen package lifecycles,
  persistence/localization, invalid inputs and upstream dependency tests.
  Physical sensors, visual odometry and real-time operation remain unverified.
- [Local trajectory generation](probes/ruckig/README.md),
  [quadratic optimization](probes/osqp/README.md) and
  [motion planning](probes/ompl/README.md): Ruckig 0.19.4 and OSQP 1.0.0 pass
  installed macOS software contracts. Ruckig also has a GCC16 cross package
  with installed numerical contracts, all 15 bounded upstream groups and
  removal/reinstallation verified in EmberBSD AArch64 QEMU. OSQP now has an
  installed GCC16 package with QP/KKT, infeasibility, derivative and real SIGINT
  checks. All three upstream programs and two injected allocation-failure
  regressions pass on AArch64. OMPL 2.0.2 now has a GCC16 cross package with
  common Eigen 5.0.1 and Boost 1.92.0. Installed AArch64 QEMU checks cover an
  independently validated obstacle detour, thirteen upstream programs,
  archive metadata, errors and all four package lifecycles. The
  [CSV path example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/ompl-path)
  uses the shared library. Physical collision safety remains unverified.
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
- [Speech providers](profiles/common-media/speech.md): full Sonic, eSpeak NG,
  Flite and speech-dispatcher cross packages pass CM5 language, PCM and shutdown
  regressions. [Qt TextToSpeech](probes/plasma-mobile/toolkit/tests/qt-speech/README.md)
  passes both installed engines; [KCMUtils](probes/plasma-mobile/toolkit/cross/kcmutils.md)
  passes its generated-settings test. Physical sound and interactive audio integration remain unaccepted.
- [Plasma shell libraries](probes/plasma-mobile/toolkit/cross/libplasma.md):
  complete cross packages pass installed plugin, theme and shared-QML-engine
  checks on CM5. Native KPackage metadata and common Mesa EGL selection are
  retained. Complete virtual-session acceptance is described below.
  [Current Noto fonts](probes/plasma-mobile/toolkit/cross/fonts.md)
  also pass payload, target indexing and Cyrillic/CJK selection checks.
  [ConsoleKit session launching](probes/plasma-mobile/toolkit/cross/desktop-session.md)
  now preserves child failures and passes seven real-daemon cases on CM5.
  [Registration privilege host contracts](probes/plasma-mobile/toolkit/tests/consolekit/privilege.md)
  check root-only parameter overrides and reject child execution after failed registration.
  [NetBSD process snapshot host contracts](probes/plasma-mobile/toolkit/tests/consolekit/process-query.md)
  check complete live records before metadata use; full target compilation awaits cross-built GLib.
  Graphical login and physical-device ownership remain unaccepted.
- [KWin on physical CM5](probes/plasma-mobile/toolkit/cross/cm5-kwin.md):
  KWin 6.8.0nb1 selects OpenGL ES/V3D under a non-root user.
  Desktop 6.8.0 and Workspace 6.8.0nb3 are cross-packaged and installed.
  A 333-package set passes archive, dependency and ELF-provider checks.
  The shell now passes the [bounded Desktop test](probes/plasma-mobile/toolkit/tests/plasma-desktop/README.md)
  with Mesa nb8: V3D pixels, six layout checks over 30 seconds and normal exit.
  The [Mesa Wayland allocation repair](profiles/common-graphics/tests/mesa-wayland-oom/README.md)
  also retains its actual-source failure/retry checks.
  The installed Qtbase 6.12.0nb2 runtime passes the
  [complete session test](probes/plasma-mobile/toolkit/tests/plasma-session/README.md)
  twice with V3D, Xwayland, Activities, the original five-second query deadline,
  30 seconds of liveness and normal logout. Readiness takes 18.408 and 15.661
  seconds from controller start. BO usage returns to its initial value; recorded
  temperature stays below 58 degrees Celsius without throttling or undervoltage.
  Graphical login, physical input, HDMI/KMS, hotplug, remote display and
  long-duration stability remain unaccepted.
  The current xdg-user-dirs 0.20
  cross package passes private-profile checks on CM5.
  [Desktop package preparation](probes/plasma-mobile/toolkit/cross/desktop-package-set.md)
  now includes the Activities service, current Xwayland/libei/basu providers,
  cross XKB paths and repaired native QtDBus generators for KWin's property XML.
  Its auditor rejects stale library providers, self-dependencies and package-managed
  ABI requirements missing from the selected payload before transfer.
  It also rejects serialized host interpreters and helper paths before copying archives.
  Package-set and session-runner host checks pass. The session runner checks the
  system bus before launch and preserves query statuses and phases. The installed
  CM5 virtual-session result above includes normal startup and logout.
  [Current desktop providers](probes/plasma-mobile/toolkit/cross/desktop-providers.md)
  add an SDL3 controller adaptation with eight CM5 cases and a UBSan repeat.
  Core event sounds retain their backends without mandatory GTK. Fcitx5/Qt6
  source candidates replace the compulsory IBus dependency; target input remains unaccepted.
  KIO MTP/audio plugins are installed and linked on CM5. Input prerequisites
  pass 264 UnitTest++ cases and 295 JSON assertions. Enchant passes 434 main
  and 25 Hunspell tests on CM5; full input acceptance remains pending.
- [Plasma volume controls](probes/plasma-mobile/toolkit/cross/plasma-volume.md):
  Plasma PA 6.8.0 and PulseAudioQt 1.9.0 pass seven installed component tests
  and a real QML import on CM5. Physical sound and interactive audio integration
  remain unaccepted.
  [KDE runtime repairs](probes/plasma-mobile/toolkit/tests/runtime-source-contracts/README.md)
  fix the D-Bus wait helper's argc lifetime and error result, and restore KDirWatch's fallback.
  The updated target packages pass four helper cases and 38 KDirWatch cases.
- [Media and OpenCV videoio](probes/media/README.md): FFmpeg 9.0.2,
  GStreamer 1.28.7 and OpenCV 5.0.0 pass installed file/video pipeline checks
  on AArch64, including both videoio backends, timestamps, seeking, lossless
  output and malformed input. Camera capture and acceleration are unverified.
  The [FFmpeg GCC16 CPU package](profiles/common-media/cross/README.md) also
  passes real package/dependency cycles, exact FFV1 pixels, timestamps, filters
  and PCM samples in AArch64 QEMU. The current XML provider retains its ABI,
  repairs a schema shift and passes target contracts plus native UBSan tests.
- [H.265 over RTP with FFmpeg and GStreamer](profiles/common-media/rtp/README.md):
  GCC16.2 cross builds pass installed C API checks in AArch64 and AMD64 QEMU.
  Both directions recover from packet loss, duplication, reordering and a blackout.
  A fresh receiver also resumes after closing and rebinding its UDP socket.
  Thirteen real packages pass dependency protection and removal/reinstallation;
  independent captures and pixel checks verify recovery. See the
  [results and limits](profiles/common-media/rtp/results.md).
- [CIX P1 codec prerequisites](profiles/common-media/cix-vpu/README.md):
  GCC16 cross-builds the real FFmpeg M2M backend and GStreamer V4L2 plugin.
  EmberBSD/AArch64 VM checks cover missing-device refusals and repaired
  semaphore cleanup. The native CIX driver and hardware H.265 remain unfinished.
- [Four H.265 streams through Qt Multimedia](profiles/common-media/qt-four-streams/README.md):
  a GCC16 amd64 CPU profile uses Qt 6.12 and the common FFmpeg9 provider.
  The example verifies decoded pixels and reads the actual Qt framebuffer.
  Four 2048×1500, 9 fps inputs pass an installed amd64 VM run in a
  640×480 raster window, including fourteen-package removal/reinstallation.
  See [measurements and validation limits](profiles/common-media/qt-four-streams/results.md).
- [MQTT smart-home foundation](probes/mosquitto/README.md): Mosquitto 2.1.2
  builds with common GCC 16.2, cJSON 1.7.19 and SQLite 3.53.4. Twelve installed
  AArch64 VM cases pass MQTT 3.1.1/5 QoS 0/1/2, authentication/ACL, verified
  TLS and retained-state recovery. Packaging, boot service and other
  smart-home ports remain pending.
- [Command shells](profiles/shells/README.md): dash 0.5.13.5 has a GCC16
  control with current libedit 20260512-3.1 and ncurses 6.6, source repairs,
  terminal tests and memory checks. Static analysis retains inherited
  findings for review. mksh R59c adds allocation and arithmetic repairs,
  a GCC16 control and the upstream regression suite. zsh 5.9.2 is the next
  separate control; target package and ARM64 acceptance remain open.
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
  inquiry with correct directions. Stage two's quick batch
  follows on the same board: lldpd advertises the chassis and its LLDP
  frames verify on the wire, arp-scan enumerated the local /24 without
  kernel drops, mtr/fping produce latency and loss reports, and tcpreplay
  4.4.4 replays saved captures with rate control (cross port with C23 and
  POSIX_SHELL fixes). Wi-Fi monitor mode, Lua dissectors and the GUI
  remain separate queue items.
- [Local AI CPU packages](profiles/ai-cpu/README.md): pkgsrc recipes for
  llama.cpp 0.6.0nb1 and whisper.cpp 1.9.5. Linux GCC16 cross compilation,
  target package installation, real llama.cpp text/HTTP generation and Whisper
  WAV transcription pass in an EmberBSD AArch64 QEMU VM. See the
  [Whisper record](profiles/ai-cpu/cross/whisper-validation.md) for exact words,
  JSON timestamps, error contracts and memory checks. Historical native ARM64
  tests have separate validation records.
- [ONNX Runtime CPU API](probes/onnxruntime/README.md): the canonical 1.31.0
  recipe provides a shared C/C++ CPU interface, GCC16 cross-build helpers and
  the common Eigen 5.0.1 provider. Internal build dependencies remain private.
  Installed C/C++ inference, Silero compatibility, 76 selected upstream tests
  and package removal/reinstallation pass in EmberBSD AArch64 QEMU.
  [Validation](probes/onnxruntime/VALIDATION.md) separates installed API checks,
  native memory analysis and EmberBSD AArch64 target execution.
- [ncnn CPU inference](probes/ncnn/README.md): the canonical 20260526 shared
  C/C++ SDK cross-builds with GCC16. Installed CNN inference has independent
  scalar answers, eight unchanged upstream programs, source regressions and
  package removal/reinstallation in EmberBSD AArch64 QEMU. The
  [validation record](probes/ncnn/VALIDATION.md) distinguishes target execution,
  native memory checks, ABI controls and source-analysis limits.
- [CPU inference and audio](probes/ai-engines/README.md): ncnn 20260526,
  RNNoise 0.2 and Silero VAD 6.2.3 use installed C/C++ consumers. The current
  source profile shares the canonical ONNX Runtime 1.31.0 and ncnn profiles
  and patches. The combined native build has not been rerun after this update.
  Historical ONNX Runtime 1.30.0 measurements cover seven native AArch64
  contracts for inference, stream state, speech/silence and invalid inputs.
  Worker affinity has a separate historical check. Microphones and accelerators
  remain unverified.
- [LiteRT and LiteRT-LM](probes/litert/README.md): LiteRT 2.2.0 provides a
  shared C/C++ CPU runtime for `.tflite` models; LiteRT-LM 0.18.0 adds a
  SentencePiece language-model engine. The macOS-to-AArch64 source profile
  passes installed C/C++ numerical/error contracts and real TinyLlama text
  generation on a physical A733 board. Explicit metadata preparation preserves
  the model's weights and tokenizer. These are source builds, without GPU/NPU
  validation; the profile records memory use and model limits.
- [A733 accelerator audit](probes/a733-accelerators/README.md): compiled vendor
  and Mesa feature tables identify the VIP9000 NPU's missing TP path and MMU
  differences. Exact PowerVR firmware is pinned. Native power, clocks and
  firmware bootstrap now pass on Zero 3W. Firmware reports startup and the
  expected BVNC through coherent memory. Native LOGTYPE and MMUCACHE also complete
  with verified return words and queue progress. The checked Mesa compiler
  packet now passes native GPU submission: the guarded store, client queue,
  timeline, and fresh fault checks agree on Zero 3W. This is one diagnostic
  dispatch after a fresh boot. GPU rendering and accelerated Plasma remain unverified.
- [Compass NPU UMD source contracts](probes/compass-umd/README.md): pinned
  upstream descriptor-zero and failure-cleanup fixes pass host/native software
  contracts; public core-count bounds pass 58 native production-extracted cases
  on AArch64/GCC 16.2, with legacy behavior preserved. The complete 27-source
  UMD cross-build and 85 actual no-device API checks also pass on A733.
  Kernel/DMA integration and model execution remain unverified.
- [SQLite and local document retrieval](probes/sqlite/README.md): SQLite 3.54.0
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
  The [Qt private mutex event](probes/plasma-mobile/toolkit/tests/qt-mutex/README.md)
  has source-level descriptor-pressure, sanitizer and target ABI checks;
  updated package and physical runtime acceptance remain pending.
  [Qt 6.12/KF6.31 source recipes](probes/plasma-mobile/toolkit/README.md)
  and the [shared FFmpeg9 recipe](profiles/common-media/README.md) pass
  source/export checks. Qtbase, SVG, ShaderTools, ImageFormats, LanguageServer and Declarative 6.12.0 now pass
  [Mac cross packaging and sysroot installation](probes/plasma-mobile/toolkit/cross/qt-packages.md).
  [Installed CM5 Core/Gui/SVG checks](probes/plasma-mobile/toolkit/tests/qt-consumer/README.md)
  pass thread signals, resources, image pixels, plugin errors and SVG replacement.
  [Qt Wayland/EGL on CM5](probes/plasma-mobile/toolkit/tests/qt-wayland-gl/README.md)
  passes V3D shader pixels, repeated processes and rejection checks with labwc.
  [Qt Quick on V3D](probes/plasma-mobile/toolkit/tests/qt-quick-gpu/README.md) also
  passes compiled QML scene/layer pixels and process restart. The complete
  Plasma migration remains pending. [Frameworks cross packages](probes/plasma-mobile/toolkit/cross/frameworks.md)
  now include six current Frameworks libraries. CM5 checks cover generated
  configuration persistence, native file events and locale lookup; shared-cache
  operation and the complete Plasma session remain pending. Native
  audio API/registration and host metadata extraction checks pass.

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
- [Installer XFCE profile](profiles/installer-desktop/README.md): pinned
  pkgsrc amd64 binaries and an original dhcpcd-ui 0.8.0 leaf adapted to GTK3.
  Source hashes, cross build, native package creation and installer contracts
  are checked. Complete amd64 UEFI USB installation, cold boot, XFCE/Thunar and
  visible network preferences pass in the paired OS candidate. Physical radios remain unverified.

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

The [toolkit export checks](probes/plasma-mobile/toolkit/tests/manifest.md) cover
all recipe directories, shared source owners, supplemental archives and patch publication.
A clean export preserves 150 complete toolkit recipes and the Boost toolset overlay.
This verifies reproducible source inputs, not a complete desktop session.

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
