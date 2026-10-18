# Common graphics source packages

The full [libspnav 1.2 provider](cross/libspnav.md) keeps Unix-socket and
X11/Magellan interfaces. Ordinary native/AArch64 GCC16 packages and complete
payload checks pass. Native real-socket lifecycle regressions pass strict
memory checks. Installed target and physical-device acceptance remain pending.

The [Lerc 4.2.0nb1 padding correction](cross/lerc.md) removes a reproduced
uninitialized Huffman checksum input. Normal GCC16 native/AArch64 packages
and all four original samples pass in EmberBSD. Package removal and
reinstallation also pass, with verified runtime providers.

[wxWidgets 3.2.12 and WebKitGTK 2.54.1](cross/wxwebkit.md) retain the
canonical WebView, media and OpenGL configuration. Both WebKit API recipes
share current sources and native generator routes. Source, GCC16 target link
and focused native Skia memory checks pass. The rebuilt Skia locale contract
passes in EmberBSD with installed GCC16 runtime nb3. Full dependency composition,
WebKit packages and GUI execution remain pending.

[Maintained FreeImage 3.19.25 and LibRaw 0.22.2](cross/freeimage.md)
provide common source recipes for OCCT image support. Source preparation,
GCC16 header selection and half conversions pass; complete codec packages
and installed OCCT image workflows remain pending.

[OpenEXR 3.5.2 and OpenJPH 0.32.0](cross/openexr.md) retain shared libraries,
tools and current system codecs. Ordinary GCC16 native/AArch64 packages pass
their static packing-list checks. Native image round trips and focused strict
memory checks pass, with all 147 native OpenEXR tests. Target codec/API checks
and normal package removal/reinstallation also pass.

The [JBIG-KIT 2.2nb1 provider](cross/jbigkit.md) keeps shared/static libraries and
all four image tools. Ordinary GCC16 native/AArch64 packages pass package checks.
Native upstream, installed-library and 14 CLI memory/image checks pass.
Target execution and TIFF integration remain pending.

The [ngspice 47 package pair](cross/ngspice.md) provides the CLI and shared
SPICE API for KiCad, with common XSPICE modules and normal pkgsrc dependencies.
Its target package and runtime checks remain pending.

The [common Eigen 5.0.1 provider](cross/eigen.md) retains `math/eigen3`,
`Eigen3::Eigen` and the full upstream headers and companion libraries. Its
ordinary GCC16 AArch64 package passes all 613 payload checks. Four native
and installed EmberBSD numerical checks pass, including normal package
removal and reinstallation. Companion BLAS/LAPACK runtime coverage remains pending.

This opt-in source profile prepares canonical MesaLib 26.2.4nb8, adapted
libdrm 2.4.134nb2, Wayland 1.26.0nb1 and wayland-protocols 1.49 for
EmberBSD/AArch64, retaining the NetBSD 11 ABI. Native builds and the explicit
[macOS cross composition](cross/profile.md) consume the existing
[common build tools](../common-build-tools/README.md): GCC16, Python3.15,
Meson1.12.1 and shared LLVM23.1.3 remain one dependency graph with final
`LOCALBASE=PREFIX=/usr/pkg`. Plasma Mobile uses this exact graphics layer.
The default, development-toolchain and common-build-tools exports keep their
original graphics recipes. The whole installed graphics stack and a Mobile
demonstration still require acceptance; individual package results follow.

The [V3D BO cache mutex repair](tests/mesa-v3d-cache-mutex/README.md) in nb8
passes actual-source lifecycle, allocation-error, sanitizer, and target analysis
checks. The complete GCC16/LLD23 package verifies all 100 installed payload entries.
Its [linker regression](tests/mesa-symbol-version/README.md) preserves the existing
libgallium symbol versions; the unchanged old consumer also passes on CM5.

Installed nb8 passes V3D shader rejection, triangle pixels, four EGL lifecycles,
and all 39 upstream invocations on CM5. `Cache.List` skips and nine NIR cases
remain disabled. Fifteen temperature samples range from 64.208 to 65.857 degrees
Celsius, without reported throttling or undervoltage.

The [Plasma Desktop probe](../../probes/plasma-mobile/toolkit/tests/plasma-desktop/README.md)
now passes on physical CM5 with this package and a virtual Wayland output.
It checks V3D rendering, visible containment pixels, six layout queries over 30 seconds and normal shell exit.
The strict unknown-output control also passes after a bounded startup retry.
The full login session and physical HDMI presentation remain separate checks.

The nb6 recipe also includes Zink and its Vulkan loader dependency.
Hardware Zink execution remains unaccepted; see [the package boundary](cross/zink.md).

The optional [PowerVR ICD](cross/powervr.md) uses the same Mesa recipe.
Its native generators run the full upstream common-shader pipeline. The nb5
package passes four native Vulkan enumeration lifecycles on Zero 3W, plus
four llvmpipe EGL/pixel cycles and all 38 target invocations. One internal
utility skip and nine disabled NIR cases remain. Native compute passes three
cycles on the accepted Zero 3W kernel. [Offscreen graphics](cross/powervr-offscreen.md)
and Plasma remain unaccepted. Earlier GL results retain their recorded package scope.

The [LLVM 23.1.3 migration](cross/mesa-llvm2313.md) records its earlier 38-test
V3D/llvmpipe scope. Current nb8 acceptance is described above.
The [process-local V3D trace](cross/v3d-bo-trace.md) records allocation requests
without changing the driver contract. A separate [bounded allocation CLI](cross/v3d-bo-alloc.md)
checks BO creation and release without GPU submission; its host contracts do not establish hardware acceptance.

The same package now enables V3D alongside VirGL and both CPU renderers.
The earlier nb3 [CM5 hardware OpenGL acceptance](cross/mesa-cm5.md) passes
four EGL 1.5/GLES 3.0 shader/pixel lifecycles at 16x16 and 1280x800, with
renderer `V3D 7.1.10.2`. All 38 upstream invocations pass, subject to the
recorded internal skips. Matching libdrm nb2 discovers native platform GPUs
without a DRM master. Mesa nb3 also repairs an upstream V3D import-allocation
failure. Remote KWin/Plasma, shared-buffer exchange and sustained desktop use
remain separate acceptance stages.

The [GCC16 diagnostic regression](cross/libdrm-gcc16.md) preserves the imported
i915 ABI and strict warnings for amd64 source compilation. Full nb4 package
and device acceptance remain pending.

The [graphics cross-build](cross/README.md) now builds the complete selected
libdrm payload on macOS with GCC16. All 26 staged entries match PLIST, and
hash, drmsl and symbol checks pass in AArch64 UTM. Device enumeration is
skipped on the current framebuffer-only kernel. Its normal libdrm package
and wayland-protocols package now also build and install into the cross sysroot.
Installed libdrm passes hash, drmsl and symbol checks on Zero 3W, resolving
the exact packaged library without loader overrides. Device enumeration
returns 77 on its framebuffer-only kernel; see the [repeat commands](cross/README.md).

The full [installed Mesa package](cross/mesa-package.md) passes four EGL/GLES
shader and pixel lifecycles through llvmpipe/LLVM23 on Zero 3W, reporting
EGL 1.5 and GLES 3.2. All 37 upstream test invocations exit zero; utility
tests report one internal skip and NIR nine disabled cases. Downstream
consumer migration and visible X11/Wayland sessions remain separate gates.
The subsequent nb2 package changes only three pkg-config files; all eight
installed ELF files remain byte-identical. Its X11 private dependency is
`xcb-xfixes`, matching Mesa's actual XCB provider. Obsolete Xlib Xdamage/Xfixes
buildlink requirements are removed, allowing normal consumer configuration.
Normal nb2 installation passes the complete payload check and four direct
EGL lifecycles on Zero 3W. The first downstream consumer,
[libepoxy 1.5.10nb2](cross/epoxy.md), also cross-builds and passes four real
EGL/GLES dispatch cycles plus four selected upstream tests there. Live
providers resolve to the installed common Mesa/LLVM closure.

The current [wlroots 0.20.2nb4 consumer](cross/wlroots-package.md) also passes
four GLES2/GBM headless lifecycles in an isolated AArch64 VirtGPU VM, repeated
after dropping root privileges. Its 1024-pixel oracle covers rectangles and
a texture; a real KMS framebuffer import and GEM_CLOSE leave the renderer's
buffer usable. The package fixes software primary-node selection and private
EGL cleanup without changing kernel permissions. The subsequent
[DRM/input package](cross/drm-input.md) presents four llvmpipe frames at
1280x800 with an active libseat session and enumerates two wscons devices.
All 131 selected dependency checks pass in the same isolated VM. Actual
input events, VT switching, application surfaces, labwc and an accelerated
session remain separate acceptance stages.
The same installed stack also passes four [offscreen guest VirGL lifecycles](cross/virgl-draw.md)
with the separate EMBERVIRGL kernel and paired ANGLE Metal host on Apple M3.
It now also passes four [accelerated wlroots DRM presentations](cross/wlroots-virgl.md)
at 1280x800, with pixel checks and clean shutdown. This requires the paired
Cocoa context repair and the guest PCI queue teardown fix. The CPU consumer
still passes on the 2D device; a complete compositor session remains unaccepted.
The [current text/image closure](cross/labwc-dependencies.md) also cross-builds
GLib 2.90.1, Pango 1.58.2, HarfBuzz 14.6.0 and Cairo 1.18.6 with normal package
checks. Four installed AArch64 VM cycles pass font selection, shaping, CPU
rasterization and PNG roundtrip with causal negative controls. Installed
[libsfdo and session D-Bus](cross/desktop-support.md) pass four unchanged upstream
lookup/parser tests and actual bus ownership, method replies, errors and shutdown
in AArch64. A [Rust 1.99 cross-std probe](../../probes/rust-cross-std/README.md)
passes target TLS/unwind and C-library consumers for the future SVG path.

The D-Bus 1.16.2nb6 recipe uses the corrected common cross configuration.
Its rc script sources base `/etc/rc.subr`; package configuration stays under
`/usr/pkg/etc`. Actual pkgsrc generation and native-independence checks pass.
Full package and installed service acceptance remain separate.
The [GI 1.86.0 cross package](cross/introspection.md) preserves the complete
selected payload and runs real GType queries on EmberBSD/CM5. Three unchanged
upstream hash/search cases also pass there.
The revision-6 GI recipe also fixes temporary hash-key and test-buffer leaks.
A GCC16 native causal check confirms the repair while preserving explicit
GLib reachable-allocation and Cppcheck parser limits; package acceptance is pending.
The matching GLib 2.90.1 metadata
package supplies all seven GIR/typelib pairs and passes four target load/invoke
cycles on CM5. The [complete text/GTK introspection packages](cross/desktop-introspection.md) also cross-build; their real GType queries pass on CM5 with the shared query transport.
The complete [GdkPixbuf 2.44.8 and shared MIME packages](cross/gdk-pixbuf.md)
preserve thirteen raster formats, introspection and thumbnailer payload;
four CM5 cycles pass complete and incremental decoding with pixel checks.
Sysroot base provenance follows
the [fork-specific requirements](../common-build-tools/cross/sysroot.md).
The [librsvg package](cross/librsvg.md) passes four CM5 CPU cycles for its C API,
CLI, dynamic loader, AVIF, text and typelib with verified MIME data.
The [labwc 0.20.2nb2 package](cross/labwc.md) cross-builds and preserves the
selected SVG, icon, translation and documentation payload. Inspection matches
62 installed files/links and 80 target ELF files.
The separate [VirGL session check](cross/labwc-session.md) passes two EGL/screencopy
and USB-input sessions on Apple M4/ANGLE Metal, including 60 additional paced
frames per session across keyboard-driven window/maximize/restore/fullscreen
transitions, plus two whole-window captures verifying USB mouse dragging.
Sustained desktop use remains unaccepted. Physical CM5 offscreen OpenGL
has its own receipt linked above.


The cross Wayland revision-2 recipes separate runtime libraries from the
target scanner and SDK. Native ownership stays complete. Actual pkgsrc metadata
and copied-stage checks pass; normal split packages and installed runtime
execution remain pending. See the [package boundary](cross/wayland.md#runtime-and-sdk-packages).

The [Wayland 1.26.0nb1 package](cross/wayland.md) passes all 26 enabled
upstream invocations on Zero 3W with the paired kernel IPC fixes. The common
[LLVM23 core](../common-build-tools/llvm-family.md) passes installed C API and
four default ORC JITLink lifecycles on that board. These results establish
library/runtime prerequisites, not a compositor or accelerated renderer.

The same cross directory contains a temporary Mesa26 headless diagnostic.
Its private softpipe bundle passed shader rejection, triangle pixels, four
EGL lifecycles and 30 selected upstream test runs on Orange Pi Zero 3W (A733).
That result excludes LLVM/llvmpipe, X11/Wayland and installed packages.

The selected APIs are X11/Wayland, EGL, GBM, OpenGL and GLES; renderers are
V3D, classic VirGL, Zink, softpipe and llvmpipe with ORC JIT. The recipe requires shared
LLVM23, upstream tests and portable TLS. It never substitutes Mesa21,
libLLVM13, another Python or native X11 GL/EGL/DRM/GLU providers. Native X11
protocol libraries can still satisfy pkgsrc's actual version checks.

The [native DRM change-event contract](cross/libudev-drm-change.md) preserves
ndevd's packet format and supplies the `drm_minor` type used by KWin.
Its causal source checks cover nb2 rejection and the nb3 parser/filter repair.
Live delivery and physical HDMI hotplug remain unverified.

## Prepare and select

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc common-graphics
# Plasma also replaces the current Qt/KF toolkit recipes:
sh scripts/prepare-pkgsrc.sh /absolute/another-new-pkgsrc plasma-mobile
```

Include the exported files in a private native MAKECONF, in this order:

```make
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-TOOLS-MK.CONF"
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
# For Plasma, include media before the toolkit:
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-MEDIA-MK.CONF"
.include "/absolute/prepared-pkgsrc/EMBERBSD-PLASMA-TOOLKIT-MK.CONF"
```

The exporter validates all six source pins, complete recipe trees and exact
RCS-filtered patch hashes before creating its destination. It replaces
`graphics/MesaLib`, `x11/libdrm`, `devel/wayland` and
`devel/wayland-protocols`, `x11/xorgproto` and `devel/libudev-bsd`
inside the new pinned pkgsrc export.
`EMBERBSD-COMMON-GRAPHICS-SOURCES` records their provenance. Unknown modes,
existing destinations and category collisions remain errors. No system
configuration or installed package is changed by preparation.

The [Wayland cross instructions](cross/wayland.md) build the matching host
scanner and run the enabled upstream suite against the installed target
libraries. NetBSD adaptations use real peer credentials and descriptor
counts; they retain upstream leak checks and test failures.

GCC selection belongs to the included common-tools configuration, including
the complete compiler package's runtime policy and native bootstrap boundary.
The graphics profile adds no second compiler policy.

The profile rejects conflicting command-line providers, dependency minima,
Meson overrides, old/unprepared recipes, cross builds without the dedicated
opt-in, another platform or prefix. Mesa substitutes one absolute common
`TOOL_PYTHONBIN` into upstream's
actual interpreter list, preserving version and Mako/packaging/PyYAML checks.
Failed imports cannot select another interpreter. LLVM's explicit absolute
`LLVM_CONFIG_PATH` reaches Meson's native or cross machine file; production
pre-configure checks reject missing metadata, another version, static-only
LLVM or missing ORC components/RTTI. There are no fallback downloads.
Cross builds additionally require the real target-metadata helper and verify
its receipt and target sysroot paths before configuration.

The build-tool layer supplies Mako 1.4.3, MarkupSafe 3.0.4 and PyYAML
6.0.3nb1. Native generator checks use the installed packages. PyYAML requires
Cython 3.3 and libyaml; its real extension is packaged and the upstream suite
passes with its documented skips. Xorgproto 2026.1 and libudev-bsd 0.7.0.1nb2
complete the current graphics dependency recipes. The
[libudev adaptation](cross/libudev-render-nodes.md) adds DRM render-node
classification for KWin 6.8 and includes source and target enumeration probes.

## Bounded package contents

Mesa enables zlib/zstd and the NetBSD libudev-bsd provider. Display-info,
libunwind, valgrind, unselected Vulkan drivers, video frontends, Rusticl/OpenCL, other physical GPU drivers,
OSMesa, XA and GLVND are outside this candidate. Requests for unsupported
Mesa options fail; they do not install older providers. Unselected optional
libelf/Lua/XCB-keysyms are absent from the buildlink sandbox.

libdrm is deliberately core-only. Intel, Radeon, AMDGPU, Nouveau, VMware and
physical ARM client modules, man pages and test-program installation are
disabled; upstream tests remain enabled. Unconditional kernel UAPI headers
remain installed. A consumer requiring `libdrm_amdgpu`, `libdrm_intel` or
another disabled client module is a migration blocker. Adapted revision
`nb2` includes PCI and platform metadata discovery and prevents an
unpatched libdrm2.4.134 package satisfying the native
identity requirement. The canonical recipe omits pkgsrc's native-X11
avoid-duplicate skip, so actual dependency selection still builds libdrm.

Both Mesa and libdrm PLISTs match their complete cross-staged payloads and
pass normal package checks. Mesa's installed CPU rendering and upstream
tests pass the separate [target acceptance](cross/mesa-package.md).
Mesa's GL/EGL/
GLES/GBM/DRM SONAME closure is GL1/EGL1/GLESv1_CM1/GLESv2 2/GBM1/DRM2,
plus `libgallium-26.2.4.so`, the GBM backend and upstream dril driver links.
`glx.pc`, `eglext_angle.h`, `gbm_backend_abi.h` and both upstream drirc
configuration defaults are included. Defaults remain in `share/drirc.d`;
an existing user drirc must be preserved independently. OSMesa/XA, video,
physical aliases and the old shared libglapi files are removed from PLIST.
Mesa26 shared-glapi is private/static within gallium, with no replacement DSO.

Normal same-pkgbase upgrade handles old Mesa-owned files. Separate installed
`libglapi`/`libglvnd` providers conflict explicitly; these are package-database
conflicts, not invented recipes in this pkgsrc pin. Never delete base X11
files or fabricate SONAME links. Native transition requires an ownership and
reverse-dependency inventory and actual rebuild of GLU, libepoxy, Qt/KF,
compositor and all installed/dynamically loaded graphics consumers.

## Provenance and verification

The recipe base is pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
The shared libffi 3.8.0nb1 recipe rebases its inherited PowerPC header patch.
It preserves both original ILP32 guards. The [source regression](tests/libffi-rebase.rb)
reproduces the stale hunk failure and applies all thirteen canonical patches.
It checks the exact rejected hunk, independent of host diagnostic wording.
This source check does not test PowerPC execution.
[sources.tsv](sources.tsv) records original URLs and SHA256; distinfo also
records BLAKE2s, SHA512, size and filtered patch SHA1. Original RCS identifiers,
ownership and licences are retained. Local work is AI-assisted and has not
been submitted or accepted upstream.

The four exact accepted Mesa patches and the complete 44-patch disposition
belong to [the source probe](../../probes/wayland-utm/mesa-patches.md).
The package additionally selects the explicit build-host Python and groups
compound-literal arguments in six colour-matrix copies for NetBSD's fortified
`memcpy` macro. The latter preserves the matrix values and SSP checks; it is
covered by an actual GCC16/NetBSD-header compile regression.
The pkg-config patch replaces the stale `xfixes` requirement with the already
selected `xcb-xfixes`. The real installed metadata failed before this change;
all seven modules now resolve and compile an EGL/GLES/GBM consumer. Normal
package checks and a full rebuild verify that this changes no Mesa ELF payload.
All seven imported libdrm patches plus the three accepted symbol/identity/
strict-warning patches remain byte-identical to
[their owner](../../probes/wayland-utm/native-identity.md). Disabled-module
patch hunks remain for provenance; their presence does not imply those modules
were built. The only unsupported-bus warning exception remains the narrow
`-Wno-error=cpp` used by the accepted strict-warning adaptation.

Run lightweight source checks with existing BSD make, Ruby, a C compiler,
OpenSSL with BLAKE2s, shasum, tar and patch:

```sh
sh profiles/common-graphics/tests/source.sh VERIFIED_DISTFILES NEW_WORK
sh profiles/common-graphics/tests/export.sh NEW_WORK
sh profiles/common-graphics/tests/mesa-bundle-integrity.sh NEW_WORK
BMAKE=/absolute/bmake sh profiles/common-graphics/tests/profile.sh EXPORTED_PKGSRC NEW_WORK
BMAKE=/absolute/bmake sh profiles/common-graphics/tests/qtbase-egl.sh QTBASE_MAKEFILE NEW_WORK
BMAKE=/absolute/bmake sh profiles/common-graphics/tests/selection.sh \
    EXPORTED_PLASMA_PKGSRC NEW_WORK
TEST_PYTHON=/absolute/host-python3.15 TEST_MESON=/absolute/meson-1.12.1/meson.py \
BMAKE=/absolute/bmake ruby profiles/common-graphics/tests/configuration.rb \
    PATCHED_MESA NEW_WORK
```

For the final command, supply verified upstream Mako/MarkupSafe source paths,
packaging and PyYAML through `PYTHONPATH` when the host lacks them. No helper
installs packages. Its actual Meson fragment executes production interpreter
selection and upstream option declarations. Production recipe LLVM guards
use explicit metadata fixtures. Full-recipe selection executes pkgsrc's real
builtin/buildlink/dependency logic, using the exact pinned pkgtools dewey
matcher with narrow host header glue and declared target/installed-option
metadata. These host checks are not native Mesa configuration or compilation.
They retain host-only dlopen/license premises as failures, not fake success.
Upstream megadriver installation executes against dummy staging to verify
real relative link targets and master retention; it is not native staging.

Accepted lifetime/half-float/libdrm-identity contracts are referenced, not
rerun as package evidence. The new checks cover archive/patch integrity,
zero-fuzz once-only applications, import/tool failures, provider/version
selection, export composition and temporary-archive failure cleanup.

## Target package and consumer acceptance remain mandatory

The common LLVM23 runtime and complete Mesa26 cross package now pass target
API, normal packaging and installed CPU-rendering checks. Mesa's cross build
also passes eight host source/ELF tests. Repeat the installed tests with the
[package runner](cross/mesa-package.md) and verify package ownership.
Normal `check-files`, shared-library/RPATH/WRKREF and installed pkg_admin checks
remain required for subsequent rebuilds. No skip list exempts a file.

Then rebuild and inspect affected consumers, including loaded dril/GBM/Qt
plugins: exactly one Mesa/DRM/sharedLLVM/GCC16 runtime, no libglapi, old base
GL3/EGL0/DRM3, build paths or loader overrides. NetBSD clients loading worker
libraries need pthread at process startup. Consumer graphics checks,
application surfaces, physical input events, VT recovery and sustained
VirGL sessions remain runtime gates.
The [common media profile](../common-media/README.md) prepares FFmpeg9 for
Qt Multimedia/KFileMetadata; native packages and playback remain unaccepted.
Physical GPU acceleration and the complete Mobile workflow remain unverified.
