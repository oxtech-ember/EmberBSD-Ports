# Common userspace migration for Plasma

Build the current shared package stack on the development host first. Run
package and desktop acceptance on EmberBSD. Cross compilation is the preferred
path; a native-only step needs a specific missing capability and a Ports fix.
The former VM-only resource plan does not constrain the cross build.

## One dependency stack

Use GCC 16.2, Python 3.14.8, Meson 1.12.1, shared LLVM 23.1.2,
Mesa 26.2.4, Qt 6.12.0 LTS and Frameworks 6.31.0. Keep their common recipes,
ABI and final `/usr/pkg` prefix. Do not add older providers for one consumer.
The toolkit's final Qt prefix is `/usr/pkg/qt6`.

The [common graphics acceptance](../../../profiles/common-graphics/cross/mesa-cm5.md)
records hardware OpenGL and same-device PRIME/EGLImage on CM5. It does not
establish a desktop. The [cross workflow](cross/README.md) prepares matching
Qt host generators; an older host Qt is not an interchangeable dependency.

## Build and validation sequence

1. Record the fork sysroot's provenance, GCC runtime, common package inventory,
   target kernel and recovery artifacts. Keep host packages separate from target
   packages, including their output directories and package databases.
2. Build the matching Qt host generators. Verify executable versions, generated
   code, shader compilation and malformed-input handling. Keep native generator
   libraries outside the target sysroot.
3. Cross-build the C++ dependencies, Qt and Frameworks through the prepared
   pkgsrc recipes. Preserve full development components. Check manifests,
   installed ELF dependencies and that target tools do not contain host paths.
   A successful configure or source check is insufficient.
4. Run installed Qt consumers on EmberBSD: Core threads/signals and resources,
   plugin loading, real EGL/OpenGL pixels, Quick shaders and Wayland surfaces.
   Test errors, exit/restart and release of GPU resources. Confirm the actual
   V3D renderer and current Mesa/LLVM libraries in the live process.
5. Rebuild KWin 6.7.5, Workspace and the selected Plasma shell against this same
   package set. Resolve consumer incompatibilities in Ports. Preserve global
   shortcuts and the platform adaptations from the existing KWin probe.
6. Accept the first CM5 session through HDMI: confirm firmware/framebuffer
   handoff, a usable display backend, KWin presentation and physical input.
   Offscreen V3D rendering does not establish a display output.
7. Then accept the remote session using KWin's virtual output with its
   render-node EGL backend and remote capture/input.
   The current KRDP source path requires KPipeWire, FreeRDP/WinPR, QtKeychain
   and PAM; systemd integration is optional. Port those dependencies instead
   of treating Linux service management as a platform requirement.
8. Verify remote authentication, repainting, keyboard/mouse input, application
   launch, a saved text edit, disconnect/reconnect and a second clean session.
   Record resolution, renderer, loaded libraries, duration and resource use.
   Retain the separate [Mobile acceptance](../kwin/MOBILE-GRAPHICS-CONTRACT.md)
   when validating a physical Mobile display and on-screen keyboard.
9. Check affected shared consumers and ordinary package replacement/removal/
   reinstall. Update the implementation receipts and central EmberBSD README
   only to the level actually measured. Remove obsolete comparison builds
   after preserving their logs and required recovery artifacts.

## Resource and recovery rules

Choose build parallelism from measured host RAM and storage. Keep source
archives, objects, packages and logs on the selected build filesystem. A failed
build retains its status and diagnostics; an old binary is not its output.
Do not remove unrelated work to recover space. Remove owned failed or redundant
objects once the cause is recorded and reproducible inputs remain available.

Before installing on a device, preserve its actual package inventory and
recoverable boot set. Kernel and modules must come from the same verified
bundle. Experimental CM5 PRIME acceptance does not authorize substituting
upstream NetBSD base files or a mixed sysroot for EmberBSD.

## Remaining acceptance boundaries

Qtbase, SVG, ShaderTools, ImageFormats, LanguageServer and Declarative pass cross-package and build-sysroot checks;
[the package receipt](cross/qt-packages.md) records the boundary.
The [CM5 Core/Gui/SVG consumer](tests/qt-consumer/README.md) also passes runtime
and package lifecycle checks. The [Qt Wayland/EGL V3D consumer](tests/qt-wayland-gl/README.md) also passes on
CM5 with an isolated labwc output. The [Qt Quick V3D consumer](tests/qt-quick-gpu/README.md)
also passes compiled QML scene/layer pixels. The remaining module runtimes
remain unaccepted. The [common FFmpeg 9 profile](../../../profiles/common-media/README.md)
owns Qt Multimedia/KFileMetadata dependencies; source and earlier host
extractor checks do not accept complete multimedia playback. KWin, Plasma,
remote streaming/input and the Mobile workflow each need their actual runtime
checks. Build-only results must remain labelled as such.

Sources: [Qt cross compilation](https://doc.qt.io/qt-6/cross-compiling-qt.html),
[Frameworks 6.31 release](https://kde.org/announcements/frameworks/6/6.31.0/),
[KRDP 6.7.5 dependencies](https://invent.kde.org/plasma/krdp/-/blob/v6.7.5/CMakeLists.txt).
