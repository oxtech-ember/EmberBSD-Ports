# Cross-build the common wlroots GLES2 consumer

The canonical `wayland/wlroots` recipe selects upstream 0.20.2 and the same
installed MesaLib 26.2.4nb2, libdrm 2.4.134nb1, Wayland 1.26.0nb1 and shared
LLVM23 packages as the [accepted graphics stack](mesa-package.md). The
[DRM buffer prerequisite](gbm.md) passes in an isolated AArch64 EMBERGPU VM.
The headless consumer below tests a separate wlroots API boundary; it does
not establish a visible compositor, KMS scanout or physical input support.

## Package selection

Start with the [common macOS cross composition](profile.md), its accepted
sysroot, sealed target LLVM metadata helper and receipt-verified native
Wayland scanner. Use the canonical exported recipes. In the private
MAKECONF, before including the graphics profile, set:

```make
EMBERBSD_WLROOTS_PROFILE= headless-gles2
MAKE_JOBS= 2
```

Then use normal pkgsrc package targets and install their resulting packages
into the target sysroot. Build only dependencies missing from that sysroot:

```sh
cd /absolute/prepared-pkgsrc/wayland/wlroots
MAKECONF=/absolute/graphics-cross.mk.conf /absolute/host/bin/bmake package
```

This explicit interim selection enables GLES2 and the GBM allocator. It
disables the optional DRM, libinput and X11 backends, session handling,
Vulkan, color management, libliftoff, Xwayland and examples. The upstream
headless, multi and Wayland backends and core pixman region operations remain.
The runtime test requires the actual GLES2 renderer; pixman is not an
alternative renderer for this acceptance. Automatic subproject downloads
are disabled with `--wrap-mode=nofallback`.

The default `full` selection preserves all supported recipe options and
requires each selected provider. Native builds retain the full defaults.
DRM and libinput require session support; libliftoff requires DRM, and
xcb-errors requires Xwayland. The full package and its optional dependency
closure remain unaccepted. Vulkan requires a separately accepted Vulkan
provider and native glslang; the current Mesa package supplies no Vulkan ICD.
DRM resolves native hwdata metadata separately from target libraries.

| Added provider | Selected source | Scope |
| --- | --- | --- |
| pixman | 0.46.4, pinned pkgsrc recipe | Core regions and upstream CPU utilities |
| libxkbcommon | 1.13.2nb1, canonical graphics recipe | Target keyboard compiler and runtime paths |
| xkeyboard-config | 2.48nb1, canonical graphics recipe | Complete current keyboard data |
| input-headers | 1.31.3, commit `10995219206280da0f1a3ba124abe4c8ef89e021` | Build-only input codes required by core wlroots keyboard types |

The input headers come from the current BSD
[libopeninput branch](https://github.com/sizeofvoid/libopeninput/tree/10995219206280da0f1a3ba124abe4c8ef89e021).
Their exact archive URL and SHA256 are in [sources.tsv](../sources.tsv).
This package builds no libopeninput runtime. Enabling the libinput backend
still requires migration of the current runtime and the existing input
contracts; the headers package does not establish input-device support.

## Cross adaptations and causal checks

wlroots consumes the installed native `wayland-scanner.pc` and executable
through the same guarded machine metadata as Mesa and wayland-protocols.
Missing, mismatched or modified scanner artifacts stop configuration.
The six existing pkgsrc portability patches are retained. The libinput
Meson patch only refreshes its final context for upstream's keypad-slide
probe; no input feature is silently removed. Disabled-backend patch presence
does not establish that backend's build or runtime support.

The nb4 software-node patch addresses an observed target allocation failure.
Upstream GBM initialization and allocator selection prefer a render node,
but Mesa's KMS software winsys requires primary-node `CREATE_DUMB` and
`MAP_DUMB`. After EGL actually reports `EGL_MESA_device_software`, initialization
retries on the caller-provided primary device through wlroots' existing
reopen/lease/authentication mechanism, moved into a shared internal helper.
Renderer, allocator and caller use distinct file descriptions and GEM tables.
A plain `dup()` shares that table: the DRM backend's PRIME import followed
by `GEM_CLOSE` would invalidate Mesa's renderer handle. A render-only caller,
failed reopen or failed authentication fails clearly. Hardware selection
keeps its existing path; kernel device permissions remain unchanged.

The retry destroys its first context, terminates its new private EGL display,
then destroys GBM and closes its fd. Termination is necessary even without
`EGL_KHR_display_reference`, because that private display has never been
exposed to callers and must not survive with its old render-node screen.
The same cleanup handles partial display/context initialization, frees both
DMA-BUF format sets and avoids terminating an already released display twice.
The normal public destructor retains upstream display-sharing policy.
This is an EmberBSD compatibility patch with AI assistance, not an upstream
acceptance or a change to the kernel's render-node permissions.

xkeyboard-config uses xkbcomp only in its upstream symbol tests. Its cross
recipe moves that executable from `TOOL_DEPENDS` to `TEST_DEPENDS`, preserving
the native build dependency and all keyboard data. It does not introduce
an unnecessary native X11 compiler closure for data generation.

libxkbcommon's first cross package embedded the build machine's sysroot in
four runtime keyboard paths: pkgconf prepends the sysroot even to the relevant
`--variable` queries. Its nb1 recipe passes explicit target paths for the
main, legacy and two extension directories. The small Meson patch supplies
the missing legacy-root option; its empty default preserves upstream native
autodetection. A production post-configure check validates all four paths
and rejects sysroot leakage into `config.h` or `xkbcommon.pc`. No environment
override or compatibility symlink hides the original runtime failure.
This patch is EmberBSD work with AI assistance, not accepted upstream.

The scoped regressions execute actual pkgsrc selection and production
guards. Supply the original generated `config.h` and `xkbcommon.pc` captured
from the failing unadapted cross build, and the newly configured source:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/wlroots-selection.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf /absolute/new-selection
BMAKE=/absolute/host/bin/bmake ruby ../tests/xkeyboard-tools.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf \
    /absolute/original-xkeyboard-Makefile /absolute/xkeyboard-config-2.48 \
    /absolute/new-keyboard-tools
BMAKE=/absolute/host/bin/bmake ruby ../tests/wlroots-input-headers.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf \
    /absolute/wlroots-0.20.2 /absolute/cross-tools/bin/aarch64--netbsd-gcc \
    /absolute/sysroot /absolute/new-input-headers
BMAKE=/absolute/host/bin/bmake ruby ../tests/xkb-runtime-paths.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf \
    /absolute/original-generated-xkb-metadata /absolute/configured-libxkbcommon \
    /absolute/new-xkb-path-tests
ruby ../tests/wlroots-software-node.rb /absolute/original-node-wlroots \
    /absolute/previous-dup-retry-wlroots /absolute/new-patched-wlroots \
    /absolute/new-software-node-tests
```

The input test compiles actual target input codes and proves the missing-header
failure without their package include directory. The XKB check rejects the
original metadata and separate drift in every runtime root and the `.pc`
file, while preserving native selection. The software-node fixture compiles
the actual production create/destroy/fd/allocator functions against explicit
API boundary doubles. Three original failures detect the wrong software node,
the shared GEM table and a partially initialized display/format leak.
Fourteen patched software/hardware/node/error scenarios check distinct GEM
tables, authorization, ownership and cleanup with and without display references.
This deterministic check is separate from real target rendering.
A revision change may leave existing
pkgsrc completion cookies satisfied; use normal `bmake clean` for this package
before a corrected build. Preserve the original failure and package first.

`scripts/tests/prepare-pkgsrc.sh NEW_WORK` tests the export refusals on a
small fixture. It does not need disk space for a full export.

## Compile and run the real API consumer

Use the exact six package archives already installed in the sysroot and the
accepted Mesa nb2 bundle. The helper verifies their complete regular files,
symlinks and runtime libraries, then compiles with real target pkg-config
metadata and GCC16. It requires the explicit `PKG_OPTIONS=glesv2` package:

```sh
ruby prepare-wlroots-render.rb /absolute/cross-tools /absolute/sysroot \
    /absolute/host/bin/pkg-config /absolute/accepted-mesa-nb2-bundle \
    /absolute/new-wlroots-acceptance \
    /absolute/wlroots-0.20.2nb4.tgz /absolute/input-headers-1.31.3.tgz \
    /absolute/pixman-0.46.4.tgz /absolute/libxkbcommon-1.13.2nb1.tgz \
    /absolute/xkeyboard-config-2.48nb1.tgz /absolute/wayland-1.26.0nb1.tgz
ruby ../tests/wlroots-bundle.rb /absolute/new-wlroots-acceptance/bundle \
    /absolute/sysroot /absolute/new-bundle-guards
```

The bundle contains no replacement libraries and installs no packages. Its
legacy `mesa-package-files.sha256` name now records the union of the accepted
Mesa payload and all six consumer package payloads, including keyboard data
and the Wayland scanner. The target must contain the complete recorded files,
even when the small test does not execute each installed tool. An incomplete
minimal root fails verification instead of weakening this ownership check.

Install the exact normal packages on a NetBSD/AArch64 target with a real DRM
primary device supporting dumb buffers, PRIME and 32×32 KMS framebuffers.
The caller needs permission for primary-node allocation and authentication
of reopened descriptors. Verify the archive SHA256 after
transfer, extract it, and run:

```sh
sh /absolute/bundle/run-wlroots-render.sh /absolute/bundle \
    /dev/dri/card0 /absolute/new-wlroots-logs
```

The runner rejects loader, renderer and XKB overrides. Its isolated child
explicitly sets `LIBGL_ALWAYS_SOFTWARE=1` and `WLR_RENDERER_ALLOW_SOFTWARE=1`
and requires llvmpipe. It verifies the full package payload before execution,
then checks both `ldd` and live provider identities while renderer resources
remain alive. Execution is bounded to 60 seconds plus five seconds to kill.

The optional fourth runner argument `--drop-privileges` opens the caller's
DRM-master fd as root, then drops supplementary groups and all real/effective
user/group IDs to 65534 before creating the renderer. Each cycle uses a fresh
child process. Use this only in an isolated test root whose DRM node permissions
already permit that UID to reopen the device. The helper changes no accounts,
device ownership or permissions. It verifies the dropped IDs and child status.

The program first compiles the normal installed evdev/pc105/us keymap and
checks unmodified and Shift-modified A. Each of four independent lifecycles
then creates a real wlroots GLES2 renderer from the selected DRM fd, a GBM
allocator and a linear ARGB8888 DMA-BUF. Its upstream render pass draws red
and green rectangles and a blue texture; all 1024 readback pixels must match.
The caller imports that DMA-BUF into an actual KMS framebuffer without scanout,
then closes its temporary GEM handle. The renderer's existing `MAP_DUMB` handle
must still work. This exercises the DRM backend's handle-lifetime contract
even though the package's optional DRM backend is not enabled yet.
It creates a headless output, commits the buffer and requires a presentation
event before cleanup. No framebuffer stub or alternate renderer can pass.

Normal package checks and the complete guarded nb4 run pass in the isolated
AArch64 EMBERGPU VM. Four cycles pass both as root and after the explicit
drop to UID/GID 65534, with llvmpipe/LLVM23, actual KMS framebuffer handle
lifetimes, 1024 pixels, headless presentation and matched live providers.
The same framebuffer oracle against nb3 fails `MAP_DUMB` with `ENOENT`
after the caller closes its handle; it exits one rather than crashing.
On a failed GEM lifetime oracle, the test
reports failure and exits without calling Mesa with an invalid mapping;
process teardown reclaims kernel resources, without a successful cleanup claim.
The software winsys uses dumb-buffer and PRIME ioctls which this kernel does
not mark `DRM_AUTH`. The unprivileged run confirms that a proposed extra
allocator-authentication workaround is unnecessary; it is absent from nb4.

| Accepted artifact | SHA256 |
| --- | --- |
| `wlroots-0.20.2nb4.tgz` | `cf970a1a05af0cf8073d48549dea1d3460542738c43f2c46b619a8b2063a5259` |
| Installed `libwlroots-0.20.so` | `3aff850f3dac7f6504c41d794cc6117933a79e0add04dee1316e97ef399033dd` |
| Privilege-drop bundle | `9041dde4b3e598d6da284807ec3b7c21ed2ed28554a57671216ea39b5827b8b2` |
| Privilege-drop VM serial log | `a6c7d8d547e1371c211ee2cb7967c5702055bdc9bebd8bac980b624210470088` |

This headless test does not establish DRM scanout, input devices,
cross-process synchronization, a visible labwc scene or GPU acceleration.
