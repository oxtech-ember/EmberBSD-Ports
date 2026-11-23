# Full paired QEMU build on macOS

This experimental Ports recipe compiles the complete QEMU executable against
[the full patched renderer](../host/README.md). It checks the real translation
units, generated headers, library interfaces and link step that the earlier
selected-function contracts could not cover. It does not install or modify UTM.

The selected QEMU 10.0.12-utm archive and all 29 sections of the UTM v5.0.6
patch set are paired upstream inputs, not a generic current QEMU release.
Their hashes and provenance are in [sources.tsv](sources.tsv) and
[create-sources.tsv](../create-sources.tsv). The archive hash agrees with the
official GitHub release asset digest. The complete overlay applies with zero
fuzz and no offsets. The resulting files match the earlier checked projection
before the accepted CREATE/backing/lifecycle/completion/wait files are copied.
The subsequent [Cocoa context repair](cocoa-context.md) preserves the calling
renderer context across display callbacks, including fenced scanout disable.
Other QEMU and UI files retain the complete UTM overlay.

This is a compatibility target selected by the UTM renderer/UI pairing.
Moving to a newer generic QEMU requires carrying these paired changes forward
and repeating the native checks. The old installed recovery host is outside
this build; see the [version boundary](../CREATE.md#version-selection-and-recovery-boundary).
QEMU retains its original authorship and GPL licensing. Local helpers are
BSD-2-Clause under [LICENSE.tests](../LICENSE.tests), with Codex assistance.

## Prepare and build

Use the host compiler and dependencies already selected by the common tools
work. The measured build used Apple Clang 21.0.0, Python 3.14.8, Meson 1.12.1,
Ninja 1.13.2, pkgconf 3.0.7, GLib 2.90.0, pixman 0.46.4 and libfdt 1.8.1.
The renderer work directory must have completed the private host recipe.
No target LLVM, Python, Mesa or language package is rebuilt here.

QEMU's configure script creates its own Python environment. Expose the prepared
common Meson 1.12.1 distribution to the selected Python, including distribution
metadata, before invoking this recipe. A `meson.py` executable alone is
insufficient for QEMU's package discovery. The helper refuses missing/older
Meson, preventing automatic installation of QEMU's vendored Meson 1.5.0.
The local measurement packaged the already prepared common Meson source using
upstream setuptools 84.0.0 into a private host module directory. QEMU's vendored
pycotap 1.3.1 is also used; it was the current upstream release when checked.
The new helpers remain shell; these Python dependencies belong to upstream.

```sh
sh prepare.sh /cache/qemu-10.0.12-utm.tar.xz \
  /cache/utm-virglrenderer-5d26f605.tar.gz /cache/raw-qemu \
  /absolute/private/qemu-work

PYTHON=/absolute/path/to/python3.14 \
  PYTHONPATH=/absolute/private/host-python-modules \
  PKG_CONFIG_PATH=/absolute/host/lib/pkgconfig \
  PKG_CONFIG=/absolute/path/to/pkgconf NINJA=/absolute/path/to/ninja \
  sh build.sh /absolute/private/qemu-work /absolute/private/renderer-work \
  /absolute/host/libfdt-prefix
```

Use new absolute work directories. Source and installed renderer receipts are
verified before configuration. The six-worker default can be changed with
`JOBS`. The selected target is AArch64 system emulation with HVF/TCG, Cocoa,
EGL/VirGL, pixman and VNC; optional unrelated features are disabled. Downloads
are disabled. The helper builds and ad-hoc signs the executable through the
upstream target, retaining the Hypervisor entitlement. Nothing is installed
into the host system. Tool/configuration/build/DSO receipts stay in the work tree.
The `ember-classic-lifecycle` device property must exist and default to OFF.
The chosen Ninja is also passed explicitly to configure. A configuration-only
regression with a Ninja wrapper outside PATH reproduced the old helper choosing
the PATH executable, then confirmed the corrected helper selects the wrapper.
Both checks deliberately stopped before compilation; the full build was checked
separately through all 1863 build steps.

## Isolated guest check

The complete executable linked with libepoxy 1.5.10 and the patched renderer
1.3.0. All original UTM Cocoa/Metal code and actual VirtGPU translation units
compiled together. A private VM then booted the complete
[VirtGPU trial kernel](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/kernel-boot.md)
with a 64 MiB temporary FFS root containing the documented rescue utilities,
libdrm and GEM/PRIME tests. The root runs its tests and calls `halt -p`.
No existing VM disk or network was used. `-snapshot` preserves the input image.

```sh
DYLD_FRAMEWORK_PATH=/absolute/path/to/UTM.app/Contents/Frameworks \
  ANGLE_DEFAULT_PLATFORM=metal VIRGL_LOG_LEVEL=info \
  /absolute/private/qemu-work/build/qemu-system-aarch64 \
  -name EmberBSD-VirGL-isolated -machine virt,accel=hvf -cpu host \
  -m 1024 -smp 2 -display cocoa,gl=es -serial file:/absolute/private/boot.log \
  -no-reboot -snapshot -kernel /absolute/private/netbsd-VIRTGPU_TRIAL.img \
  -append 'root=ld4a console=plcom0' \
  -drive file=/absolute/private/root.ffs,if=none,format=raw,id=root \
  -device virtio-blk-pci,drive=root \
  -device virtio-gpu-gl-pci,ember-classic-lifecycle=on \
  -net none -monitor none
```

Cocoa creates a separate test window. The experimental profile is explicitly
selected only in this isolated VM. The guest kernel still negotiates 2D only;
its VirGL gate is unchanged. Upstream libdrm hash/skip-list/device enumeration
and 32 cross-process GEM/PRIME lifetimes passed, followed by clean unmount and
QEMU exit status zero. This verifies a short 2D guest boot on the paired GL host,
not guest 3D rendering or a desktop session.

Set `ANGLE_DEFAULT_PLATFORM=metal` explicitly. Without it, the measured ANGLE
framework selected its OpenGL backend. With it, the actual QEMU renderer log
reported `ANGLE Metal Renderer: Apple M3`, OpenGL ES 3.0 and ANGLE 2.1.22612
(`40dfb3a8bd65`). This is the upstream
[ANGLE backend selector](https://chromium.googlesource.com/angle/angle/+/c85d9a19ffc0c4955d27e5823ff5bca12b9c8769/src/libANGLE/Display.cpp).
The same libdrm/GEM tests passed on both backends. The Metal run took about
nine guest seconds before clean unmount. The borrowed UTM 4.7.5 frameworks and
their hashes remain subject to the [host runtime boundary](../host/README.md).
The built QEMU SHA256 was
`8f65b7752ce5f4650f780237daeeffe24fdb86a90bfd9230db55346e92dc9159`;
absolute local library paths and signing metadata affect binary reproduction.

The direct-kernel boot has no firmware framebuffer for the controlled-console
handoff, so `console unavailable: -19` remains an excluded visible-console check.
The renderer also warns that ARB/KHR robustness is absent. Reset while commands
are live, blocked display cleanup, no-touch-after-revoke, silent errors and
remaining transfer bounds are unqualified. Guest Mesa/LLVM packages, consumer
migration, accelerated Wayland, Vulkan Compute and NPU execution remain open.
A successful process exit alone does not prove all native cleanup paths.

The separate [live-backing reset check](reset.md) subsequently passed three
actual QMP resets, four Metal renderer initializations and final quit while
the guest retained a 2D GEM resource. It uses an isolated read-only root and
does not extend this result to in-flight 3D commands or blocked display cleanup.

## First installed guest draw

The [bounded guest supervisor](run-guest-draw.rb) and [target instructions](../../../profiles/common-graphics/cross/virgl-draw.md)
record the first four-cycle Mesa26 guest VirGL GLES acceptance on ANGLE Metal.
The default workload covers offscreen shader/pixel lifecycles. An explicit
seventh argument, `wlroots-virgl`, adds QEMU USB input devices and requires the
[installed wlroots DRM consumer](../../../profiles/common-graphics/cross/wlroots-virgl.md):
four pixel-checked presentations, an active libseat session, two enumerated
input devices and verified live package providers. Both modes retain the same
host provider, timeout, snapshot and input-integrity guards.

The DRM workload passes on Apple M3 after the [Cocoa context repair](cocoa-context.md),
with the separately fixed guest PCI queue teardown. This is accelerated DRM
presentation, not application surfaces, a complete compositor session, live
3D reset or general fault recovery.
