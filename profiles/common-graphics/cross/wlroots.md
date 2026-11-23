# Migrate current wlroots and labwc to common graphics

The selected consumers are [wlroots 0.20.2](https://gitlab.freedesktop.org/wlroots/wlroots/-/releases/0.20.2)
and [labwc 0.20.2](https://github.com/labwc/labwc/releases/tag/0.20.2).
Their upstream release APIs were checked on 2026-10-08. The pinned pkgsrc
already contains these releases. The older native Wayland probe retains
0.19.3/0.9.7 for its historical evidence; it is not the new package provider.

The installed [Mesa/libepoxy result](epoxy.md) proves surfaceless CPU
rendering. The subsequent [canonical wlroots package](wlroots-package.md)
passes four guarded GLES2/GBM headless cycles in the isolated VirtGPU trial VM,
including a run after dropping UID/GID to 65534. The subsequent
[DRM/input/color stage](drm-input.md) passes four real DRM presentations and
131 dependency test invocations in that VM. labwc migration remains pending.
In wlroots
0.20.2, `render/gles2/renderer.c` requires `EGL_EXT_image_dma_buf_import`
and advertises DMA-BUF render targets. Its shared-memory allocator cannot
satisfy that renderer. `WLR_RENDERER_FORCE_SOFTWARE` selects a software EGL
device but does not add a shared-memory GLES render-target implementation.

The selected Mesa package already builds `kms_dri_sw_winsys.c` with
`HAVE_DRISW_KMS`. Its real DRM winsys implements dumb buffers and PRIME
import/export. llvmpipe advertises DMA-BUF capabilities when that winsys
provides a device fd. This is a source-based reason to test CPU GLES through
a real DRM device; a framebuffer-only board is insufficient. No Mesa rebuild,
fabricated DMA-BUF handle or pixman substitution is part of this preflight.

## First gate: actual DRM buffer interchange

Use the existing common cross tools, installed canonical MesaLib 26.2.4nb2
closure and its accepted package manifest from [Mesa package acceptance](mesa-package.md):

```sh
ruby prepare-mesa-dmabuf.rb /absolute/cross-tools /absolute/sysroot \
    /absolute/host/bin/pkg-config /absolute/accepted-mesa-bundle \
    /absolute/new-dmabuf-work
```

The helper checks all installed Mesa files, links and runtime hashes before
compiling `mesa-dmabuf.c` through actual target pkg-config metadata. It records
the compiler, headers, source, command, target ELF and provider manifests.
The archive contains no private libraries and installs no packages.

Prepare an isolated NetBSD/AArch64 target with the exact canonical packages
and a real DRM device supporting GEM dumb buffers and PRIME. Verify the
archive SHA256 after transfer, extract it, and select the verified device:

```sh
sh /absolute/bundle/run-mesa-dmabuf.sh /absolute/bundle \
    /dev/dri/card0 /absolute/new-dmabuf-logs
```

The child receives `LIBGL_ALWAYS_SOFTWARE=1` explicitly and must report
llvmpipe. This selects the CPU renderer while retaining real device buffers;
it is not a GPU acceleration claim. Loader overrides are rejected. The runner
verifies complete package manifests and `ldd` paths before execution. It also
checks the live `dl_iterate_phdr` inventory against the accepted runtime manifest
while the GBM device, BO and EGL context remain alive. An additional unrecorded
GBM backend fails this check even without loader environment overrides. It retains
the exit status and bounds execution to 60 seconds plus five seconds to kill.

Each of four cycles creates a GBM device and EGL context, allocates a linear
ARGB8888 BO, exports a PRIME fd and imports it as an EGLImage. The import uses
the actual offset/stride and exact linear modifier. After closing the export
fd, GLES draws a green triangle over a red background in the imported target.
`glFinish`, GLES readback and CPU mapping of the original BO must agree on
all 256 pixels. Each cycle destroys the GL/EGL/GBM objects and closes fds.
Missing devices, extensions, allocation/import support or wrong pixels fail;
they do not count as a successful skipped renderer.

The [guarded target run](gbm.md) passed all four cycles in an isolated AArch64
VM with the EmberBSD `bd158` VirtGPU trial kernel and real virtio GPU GEM/PRIME
support. It reported linear BOs with stride 256 and offset zero. Complete
package hashes, `ldd` and live-provider checks passed; the runner exited zero.
This establishes CPU rendering into actual device buffers in that VM.

This proves a same-device roundtrip: Mesa's GBM EGL path reuses its DRI screen,
and the KMS software winsys can reference its already-owned imported handle.
It does not establish first import of a foreign BO, cross-process producer
synchronization or guaranteed zero-copy transfer. It is a prerequisite for
the selected wlroots GLES2 experiment, not an independent compositor result.

## Dependency and cross-build boundary

The minimum wlroots core adds pixman 0.46.4, libxkbcommon 1.13.2nb1,
xkeyboard-config 2.48nb1 and build-only input-headers 1.31.3 to the accepted
Mesa/DRM/Wayland packages. These are
current stable versions from their upstream tags; xkbcommon 1.14 beta is
excluded. Pixman is also a core region dependency; linking it does not mean
the acceptance test may select its renderer instead of GLES2.

The final DRM/input package additionally needs libseat, libopeninput,
libdisplay-info, hwdata and optional libliftoff; X11 and color management have
their own XCB and lcms2 dependencies. Preserve supported recipe options and
make their dependencies explicit. Vulkan needs a separately accepted provider
and a real native shader compiler. Do not silently omit a requested feature.
The [DRM/input/color stage](drm-input.md) records the current dependency pins,
native metadata guards and explicit `drm-gles2` package selection.

wlroots requires native `wayland-scanner.pc` metadata, not just a binary.
Reuse the [validated scanner composition](profile.md) and its real installed
receipt. DRM's native hwdata lookup and Vulkan's native glslang are separate
host inputs; target pkg-config paths must not impersonate them.

labwc also adds Cairo/GLib/Pango/fonts, icon and SVG providers. Their complete
current dependency graph is a later build stage. A renderer preflight or
headless wlroots API test does not establish a visible labwc session, input,
KMS scanout or long-running compositor stability.
