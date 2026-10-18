# wxWidgets and WebKit source boundary

The common graphics profile selects wxGTK32 3.2.12. This is the current
maintenance release of the stable 3.2 branch. Upstream states that it preserves
the API and ABI of earlier 3.2 releases. The separate 3.3 branch is not selected.

Use the [official release asset](https://github.com/wxWidgets/wxWidgets/releases/tag/v3.2.12),
not GitHub's generated source archive. The release asset includes the upstream
submodules. Its SHA256 is
`a62719bb5e1dcc41c1a6fc1eecd499c7ee8521f70402c7b1bb3342a1e16344e0`.
The downloaded bytes match the release API asset digest. The recipe also records
BLAKE2s, SHA512 and size.

The recipe retains the pinned pkgsrc 3.2.11 configuration and complete PLIST
sets. Its three existing patches apply to 3.2.12 with zero fuzz. They preserve
SunOS library naming, the Wayland guard and the statvfs selection. The default
build uses Autoconf; the existing CMake option remains available. System codecs,
OpenGL, GTK3 WebView and media control remain enabled. The recipe keeps its
WebKitGTK 4.1, GStreamer core/base/bad, GTK3, Mesa and GLU dependencies.

Actual native Linux and AArch64 cross `bmake show-vars` select version 3.2.12,
Autoconf and the same feature flags and dependency families. The graphics
exporter's complete source and patch preflight passes. These are source and
metadata checks. The cross configuration still reports its missing X11 base
path; the native configuration has no package failure reason. Neither result
establishes a complete configure, library build, installed PLIST or GUI runtime.

## WebKit upgrade audit

The published wxWidgets recipe still depends on the canonical WebKitGTK
provider. Its upgrade is a separate pending change. The upstream
[WebKitGTK 2.54.1 release](https://webkitgtk.org/2026/10/02/webkitgtk2.54.1-released.html)
archive has SHA256
`ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d`.
The downloaded archive matches the publisher's checksum file. This check does
not claim verification of the separate detached signature.

The current pkgsrc `webkit-gtk41` and `webkit-gtk60` recipes share one source
version, patch directory and distinfo. An update must preserve that relationship.
Of the 28 existing patches, 19 apply to 2.54.1 with zero fuzz. The other nine
need source review, not relaxed patch matching:

- The old ARM64 cache-flush patch replaces an unsupported-platform error with
  a warning. It does not implement NetBSD instruction-cache synchronization.
- `MathExtras.h` now provides the round-to-even functions. The old MathCommon
  patch replaces those calls with self-calls; it must not be copied blindly.
- The old Skia `GrAutoLocaleSetter.h` became `src/core/SkAutoLocaleSetter.h`.
  The current sysroot lacks its `uselocale` API. The old NetBSD patch makes
  this helper a no-op; moving that patch would retain a limitation, not prove
  locale-independent shader formatting.
- The X11 `Status` collision and two `std::isnan` fixes need refreshed context.
- The non-Linux DMA buffer guard and platform JIT defaults need refreshed context.
- `ProcessLauncherGLib.cpp` already uses four arguments. Its old argument-count
  patch is obsolete.

The existing pkgsrc JIT option defaults to off and selects the C loop. Keep
this explicit inherited configuration until a real modern build proves the
reported `OpcodeOrigin` failure resolved. The new header's WebAssembly guard
alone is not that proof. Do not suppress cache-flush errors or fabricate a JIT
implementation.

## Cross generators and media

WebKit 2.54.1 requires C++23 and Ninja for GTK. Its GTK3/Soup3 API 4.1 remains
supported. Preserve the selected X11/Wayland backends, GL, video, WebAudio,
WebRTC, introspection and documentation. Existing recipe options and upstream
platform defaults must remain explicit; missing dependencies are not a reason
to add feature-disable flags.

The canonical recipe's legacy `PYTHON_EXECUTABLE` and `RUBY_EXECUTABLE` values
currently point into the target prefix in cross metadata. The common Python
framework separately provides the correct native `TOOL_PYTHONBIN`. A reviewed
recipe update must route build scripts, CMake interpreter queries, gperf and
other generators to actual native providers. Installed target scripts must keep
their target interpreter paths.

The actual upstream builtins generator passes with native Python 3.15.0 on
all 25 JavaScript inputs listed by the release CMake file. The upstream bytecode
generator passes with native Ruby 3.3.8 and the release bytecode and Wasm inputs.
The seven generated files are nonempty and have recorded hashes. This checks
those generators, not every WebKit script or the eventual pkgsrc Ruby provider.

The LLInt settings and offset extractor binaries describe target layouts.
Upstream Ruby reads their bytes; it does not execute those target binaries.
Do not replace them with host-ABI extractors or invented offsets. Introspection
must use the common target-query mechanism and actual target libraries.
The existing `devel/libatomic` dependency also needs an explicit audited GCC16
runtime provider selection; a second old GCC runtime is not an equivalent ABI.

For E14, compose the entire [common media profile](../../common-media/README.md):
GStreamer 1.28.8 and FFmpeg 9.0.2. The core, plugin families and shared version
metadata must change together. A partial plugin overlay would mix source
versions. This source checkpoint does not install or accept that media graph.
