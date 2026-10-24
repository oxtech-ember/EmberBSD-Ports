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

The AI-assisted cross recipe enables pkgsrc `USE_GNU_CONFIGURE_HOST`.
The GNU configure framework supplies the selected `--build` and `--host`
tuples. Upstream then selects the NetBSD GTK toolkit and cross compiler mode.
Native Autoconf builds retain their existing host autodetection.

Actual native Linux and AArch64 cross `bmake show-vars` select version 3.2.12,
Autoconf and the same feature flags and dependency families. The graphics
exporter's complete source and patch preflight passes. These are source and
metadata checks. The cross configuration still reports its missing X11 base
path; the native configuration has no package failure reason. Neither result
establishes a complete configure, library build, installed PLIST or GUI runtime.

## WebKitGTK 2.54.1

The common `webkit-gtk41` and `webkit-gtk60` recipes share the official
[WebKitGTK 2.54.1 release](https://webkitgtk.org/2026/10/02/webkitgtk2.54.1-released.html),
patch directory and distinfo. The archive SHA256 is
`ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d`.
The bytes match the publisher's checksum file. This does not establish
verification of the separate detached signature.

All 27 selected patches pass pkgsrc checksum verification and apply with zero
fuzz. Nineteen pinned pkgsrc patches remain unchanged. Refreshed patches retain
the X11 macro, numeric classification, DMA buffer and platform JIT boundaries.
Upstream already supplies the old round-even and process-launch fixes.
The ARM64 patch now calls GCC's real instruction-cache synchronization builtin.
It does not replace an unsupported-platform error with a warning.

GTK API 4.1 and API 6.0 keep their shared source version and separate libraries.
Actual upstream CMake version calculations produce `0.24.4` and `0.11.8` for
API 4.1, and `4.19.4` and `1.8.8` for API 6.0. The recipes update these four
PLIST names. Complete installed PLIST validation remains pending.

The recipes select C++23, GCC16 and Ninja. Canonical X11/Wayland, GL, video,
WebAudio, WebRTC, introspection, documentation and existing options remain.
The inherited default keeps JIT off and the C loop on. The cache-flush source
check does not establish that a complete modern JIT build works.
Release C and C++ flags use `-O2 -DNDEBUG` to keep the GCC16 WebKit cross-build
optimized while avoiding the excessive compile cost of `-O3` on large unified
source files.

## Native generators and target queries

The shared WebKit source skips Apple SDK initialization for an explicit
non-Apple target, including GTK and WPE cross builds.
The release otherwise selects that initialization from the Darwin build host
before `project()` can load the target platform. A Darwin-to-NetBSD GTK
configuration then fails despite an explicit `PORT=GTK`.
The AI-assisted repair retains native initialization and all five Apple
system names documented by CMake. It does not infer a target from the host.
Run `tests/webkit-port-sdk.py --help` from the common graphics profile for
the source-prefix regression. It executes the real SDK module before and
after the repair. Full configuration and packaging remain separate checks.

Build scripts use native `TOOL_PYTHONBIN`, the selected `${RUBY_NAME}` below
`TOOLBASE`, and native gperf. Both current and legacy CMake Python variables
receive the native interpreter. Ruby uses CMake's `Ruby_EXECUTABLE` spelling.
Build-only shebang replacements retain that separation. No installed target
script acquires a private native interpreter path.

Actual `bmake` metadata selects Python 3.15 and Ruby 4.0 for both API variants.
The upstream builtins generator passes with native Python 3.15 on all 25 inputs
from the release CMake file. The real color-table generator passes with gperf
3.3. An earlier Ruby 3.3 diagnostic produced seven builtins/bytecode outputs;
it does not validate the selected Ruby 4.0 provider. That run remains pending.

LLInt settings and offset extractors describe target layouts. Upstream Ruby
reads their ELF bytes; it does not execute them. Introspection uses the common
native scanner/compiler, ELF dependency helper and real target-query launcher.
Cross configuration rejects a missing dependency helper or launcher.
It also requires the target prefix's `share/gir-1.0` directory. Both the native
scanner and typelib compiler receive this explicit target include directory.
The compiler keeps its build directory first for generated WebKit GIR files.
Native configuration does not receive this cross-only include path.
The cross build also sets `GI_GIR_PATH` to the target GIR directory.
The native gi-docgen 2026.1 reader uses this upstream environment selector
for dependency lists and API reference generation. Generated build-tree GIR
files keep their explicit first search path. Native documentation is unchanged.
This AI-assisted recipe binding changes no target code or ABI.
The configure and build environments select the common Python query launcher.
`tests/webkit-gi-launcher.py` checks actual pkgsrc metadata for both APIs, the
release FindGI module, the launcher configuration check, native behavior and
the missing-launcher refusal. This check does not use SSH or run target code.
A complete configure still requires the native prerequisite packages and a
real target query configuration. No GType values, target offsets or configure
answers are invented.

The recipe removes the separate older `devel/libatomic` runtime dependency.
Its cross preflight verifies the actual GCC16 driver, literal target triplet,
staged library identity and target ELF ABI. Upstream atomic link checks remain.
On the actual AArch64 compiler, the upstream atomic test fails without libatomic
and links with the common GCC16 `libatomic.so.3`. Wrong-target and base-provider
controls reject their inputs. Full WebKit wrapper generation remains gated by
its ordinary dependencies; the present environment stops on missing x11-links.

## NetBSD numeric locale

Skia's NetBSD locale scope owns a genuine `newlocale` result and stores the
active scope in thread-local state. It restores the previous scope before
freeing the current object. Locale creation failure remains fatal. Scoped
formatting and parsing use the actual NetBSD `*_l` APIs. Other platforms keep
their existing locale implementation. This does not change process locale or
claim control over external libraries and asynchronous tasks.

The contract exercises actual SkString, SkSL string and SkParse APIs, nested
scopes, short/heap formatting and two concurrent workers. All 13 selected
source units compile with native and AArch64 GCC16. Native execution and strict
Memcheck pass with zero errors and no live allocations. The extra adapted
output/debug/JSON units are compiled, not exercised by this runtime contract.

Clang 19 analyzes the six changed callsite units without diagnostics. GCC16
retains reference-count, abort-path and exception-path warnings also found in
the original translation units. The JSON writer adds a modeled exception from
C `vsnprintf_l`; its normal return still reaches `va_end`. These raw warnings
remain visible. Cppcheck 2.22 cannot complete the actual target-header parse,
including a retry on genuine preprocessed inputs. This is not a clean full
static-analysis result or coverage of arbitrary formatting failures.

Target execution exposed a separate global-locale mutation in GCC16's generic
C++ numeric conversion. The [common runtime source repair](../../development-toolchain/locale.md)
passes its actual target before/after contract. The normal
`gcc16-runtime-16.2.0nb3` package and its matching development headers are now
installed in the AArch64 SDK. All 13 Skia units were rebuilt against the actual
new `bits/c++locale.h`; compiler dependency output verifies the selected header.
Native API output remains unchanged and strict Memcheck again reports zero
errors and no live allocations.

The rebuilt Skia contract also passes in EmberBSD 11 AArch64 with the normally
installed nb3 runtime and genuine `fr_FR.UTF-8` locale data: formatting, parsing,
nested scopes, both concurrent workers and ambient-locale restoration pass.
The transferred executable and all installed runtime payload entries were
hash-verified; execution used the installed loader paths without a library
search override. This accepts the exercised Skia APIs with the repaired runtime.
The extra output/debug/JSON units remain compile-only; whole Skia, WebKit and
GUI acceptance remain pending. The earlier no-op and unrepaired-runtime failures
are retained as causal evidence.

Run the bounded source and locale checks with genuine tools and a new output:

```sh
DIGEST=/native/bin/digest ruby profiles/common-graphics/tests/webkit-source.rb \
  /pinned/pkgsrc /downloads/webkitgtk-2.54.1.tar.xz \
  /cross/bin/aarch64--netbsd-g++ /sdk /new/source-check
NATIVE_CXX='/native/bin/g++ -B/usr/bin/' \
  ruby profiles/common-graphics/tests/webkit-locale/build.rb \
  /downloads/webkitgtk-2.54.1.tar.xz /cross/bin/aarch64--netbsd-g++ \
  /sdk /new/locale-check
```

The native locale test requires a genuine comma-decimal locale. Set
`COMMA_LOCALE` if its name differs from `fr_FR.UTF-8`. `MEMCHECK` can select the
actual native Valgrind command. The helper does not deploy or run target code.

For E14, compose the entire [common media profile](../../common-media/README.md):
GStreamer 1.28.8 and FFmpeg 9.0.2. Core, plugin families and shared version
metadata must change together. A partial plugin overlay would mix versions.
This checkpoint supplies source recipes and bounded checks; full dependency
composition, configure, packages, installed GI and GUI workflows
remain required.
