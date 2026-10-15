# CM5 KWin OpenGL session

The full KWin Wayland compositor runs on physical CM5 with Mesa's V3D renderer.
This is a virtual-output result. HDMI presentation and the complete Plasma
Desktop remain unaccepted.

## Runtime dependency repair

KWin 6.7.5 creates a Vulkan-Hpp context when it opens a render device.
The original package required Vulkan headers but omitted the runtime loader.
On CM5, `kwin_wayland --virtual` then called a null `vkGetInstanceProcAddr`
address in `KWin::RenderDevice::RenderDevice` and exited with SIGSEGV.
An ordinary `ldd` check cannot detect this missing `dlopen` dependency.

The common KWin recipe declares the `vulkan-loader>=1.4.357.0` runtime dependency.
The existing pkgsrc loader builds on macOS with GCC 16.2 for EmberBSD/AArch64.
It installs both `libvulkan.so` and `libvulkan.so.1` at the common prefix.
The loader recipe comes from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
Its [original archive](https://github.com/KhronosGroup/Vulkan-Loader/archive/vulkan-sdk-1.4.357.0.tar.gz)
has SHA256 `54f2537df22313768da0317dda2abdaaab7711b4081c48c869a79db343d0ae70`.
The inherited NetBSD adaptation retains pkgsrc and upstream attribution.
The same KWin binary passes the session test after this loader is installed.
No software renderer override or Vulkan-disable setting is used.
The loader has no accepted hardware ICD on this board; this is not a Vulkan result.

Run the recipe regression with native pkgsrc tools:

```sh
BMAKE=/absolute/bmake PKG_ADMIN=/absolute/pkg_admin \
  ruby tests/kwin-runtime-dependencies.rb \
  /absolute/prepared-pkgsrc /absolute/mk.conf \
  /absolute/toolkit/recipes/x11/plasma6-kwin/Makefile /absolute/new-results
```

It queries the real native and cross recipes. It requires a runtime dependency,
checks its origin and matches the selected common loader through `pkg_admin`.
The old recipe fails; the corrected recipe passes both modes.

## KWin 6.8 render-node dependency

KWin 6.8.0nb1 requires `libudev-bsd>=0.7.0.1nb2` at runtime.
The common provider must enumerate DRM render nodes before KWin can open them.
The older package constraint permitted a provider that returned no render devices.
This revision changes package metadata only. It does not change KWin's compiled code.
Use the [metadata refresh procedure](metadata-refresh.md) only with verified retained staging.
Resolve the new dependencies again; do not reuse an old resolved dependency cache.

```sh
ruby tests/kwin-package.rb /absolute/plasma6-kwin-6.8.0nb1.tgz /absolute/pkg_admin
```

The regression reads the real package metadata and uses native `pkg_admin pmatch`.
It rejects libudev revisions before nb2 and accepts nb2 and newer compatible versions.
It also rejects host paths in generated install scripts, including `SORT`.
The prior archive fails this dependency check. Package checks do not establish a new hardware session.

## Hardware check

Run [the KWin/V3D check](../tests/kwin-v3d/README.md) on the installed board.
It creates an isolated 1280x1024 virtual output and private HOME/XDG/D-Bus state.
The existing Qt Quick consumer checks two fresh processes, sixteen phases each.
Each phase checks 1024 scene pixels and 1024 layer pixels.
Wrong pixels, an absent QML module and a non-Wayland platform must fail.

The 2026-10-13 CM5 Rev 1.0 / BCM2712 D0 / 4 GiB check reports:

- KWin 6.7.5nb2, active OpenGL compositing, renderer `V3D 7.1.10.2`.
- Qt 6.12.0, Mesa 26.2.4nb4, LLVM 23.1.3 and the common GCC 16 runtime.
- Both client pixel sequences and all three negative controls pass.
- KWin exits with its client wrapper and removes its Wayland socket.
- Boot identity stays unchanged; the fan kernel is retained.
- The public wrapper also passes under an existing non-root account.
  No DRM permission or persistent service change is needed.

Kernel source: `ab6f88f04ca73c6958adb39d0e1c717f629e7901`.
Kernel SHA256: `c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.
Vulkan loader package SHA256:
`4ad2fa887dbd99730f0b21bd747b57da0a364b21b667945c29bc9283426083f2`.

The rebuilt nb2 package passes all normal pkgsrc packaging checks.
Its archive declares `vulkan-loader>=1.4.357.0` as a runtime dependency.
CM5 checks all 1756 installed entries. The repeated non-root session passes.
KWin package SHA256:
`566bf8b5768324390ad001da23c254e89af22c1e8830dacf6c096229fb50e6fd`.

The test checks client pixels and compositor backend selection.
It does not capture the final composed output or establish physical input,
login, locking, remote capture, sustained operation or HDMI scanout.

## Screen-locker installation

Kscreenlocker nb1 creates `etc/pam.d` before installing its PAM configuration.
The previous package failed to copy the file on an installation without that
subdirectory. `CONF_FILES` alone creates only the base configuration directory.

`sh tests/kscreenlocker-pam.sh ABSOLUTE_PKGINSTALL_DIR ABSOLUTE_KDE_PAM NEW_OUTPUT`
runs actual generated INSTALL/DEINSTALL scripts under an isolated prefix.
The uncorrected scripts fail. Corrected scripts pass fresh install, removal,
reinstall and preservation of an edited configuration.
The corrected package installs and checks all 199 payload files on CM5.
This is package lifecycle evidence. Interactive lock/unlock remains untested.

## Installed-resource permissions

Seven parent directories under the installed Qt QML and plugin trees had mode
0700. Root could read the modules, but an ordinary user could not load KWin's
overview QML. Their package-resource directories were restored to mode 0755.
The repeated ordinary-user session passes without the QML import errors.
Use an installation umask of 022 for shared packages. Keep private test HOME
and runtime directories at 0700. A payload hash check alone does not detect
inaccessible intermediate directories.

## Current Desktop and display boundary

The complete Plasma Desktop 6.8.0 and Workspace 6.8.0nb3 packages are installed
on the CM5 acceptance target. The separate Desktop shell is present.
The [package-set workflow](desktop-package-set.md) checks actual archive
payloads, dependencies and shared-library providers before installation.
The Configtool 5.1.16nb2 consumer uses the current `libPlasma.so.8` ABI.
Its eight installed startup and metadata checks pass under an ordinary user.
The [volume module](plasma-volume.md) passes its two unit tests and installed
QML import check. These component checks do not establish a full session.

KWin 6.8 requires DRM render-node enumeration through libudev. The original
libudev-bsd 0.7.0.1 returns no render nodes on CM5 despite an accessible
`/dev/dri/renderD128`. The [common provider adaptation](../../../../profiles/common-graphics/cross/libudev-render-nodes.md)
repairs this classification. With libudev nb2, KWin 6.8 reports active
OpenGL ES 3 compositing on V3D. Plasma Desktop 6.8 reports V3D OpenGL 3.1.
The default desktop and six panel applet models remain available for 30 seconds.
An initial empty containment capture was fully transparent. Model readiness
alone does not establish visible desktop content or a complete login session.
The [capture test](../tests/plasma-desktop/README.md) now decodes PNG pixels
and adds a visible test widget in its private desktop configuration.
Two later launches fail after large buffer allocation returns ENOMEM.
Both cores show a null image in Mesa's Wayland swap path.
The [Wayland OOM repair](../../../../profiles/common-graphics/tests/mesa-wayland-oom/README.md)
clears a prematurely cached back-buffer alias. Actual-source OOM, retry and recovery tests pass.
This repair does not establish why the kernel rejected the allocation.
The process-local trace excludes older retained BOs, imported handles and kernel storage.
It cannot establish the driver's complete allocation budget.
Native KDirWatch fallback and the D-Bus helper now pass their installed component checks.
Descriptor exhaustion in session child services remains a separate unresolved observation.

The current HDMI path displays the firmware console at 1920x1080.
The kernel exports that framebuffer through genfb/wsdisplay. A read-only
`DRM_IOCTL_MODE_GETRESOURCES` on the active V3D primary node returns
`EOPNOTSUPP`. The V3D driver advertises GEM, render nodes and sync objects,
without `DRIVER_MODESET`. Unattached static primary nodes return `ENODEV`.
Native display KMS and accelerated HDMI presentation remain unaccepted.
The virtual output size does not change the physical display signal.

## Analysis scope

The loader uses the pinned pkgsrc adaptation in `loader_environment.c`.
Cppcheck 2.22 compares that unit before and after the patch with the actual
AArch64 compile flags, target headers and compiler predefined macros.
Both versions report the same two inherited `allocaCalled` findings.
GCC 16.2 `-fanalyzer` reports no finding on either version.
Clang 23.1.3 Static Analyzer reports the same inherited dead store on line 531.
These unchanged findings belong to upstream loader code; no clean full-loader
source audit is claimed. The KWin and PAM repairs change package metadata only.
Valgrind has no validated EmberBSD/AArch64 path in this setup.
No Valgrind or sanitizer runtime pass is claimed.

## Current desktop directory helper

The Desktop closure selects xdg-user-dirs 0.20 from the official release archive.
Its Meson adaptation links the selected iconv provider, uses an absolute locale
path, and stages configuration examples through pkgsrc `CONF_FILES`.
All three patches apply with zero fuzz. A standalone GCC 16.2 cross build
installs 91 files, including both AArch64 programs, manuals and translations.
The standalone build uses the common libiconv/gettext packages. The complete
pkgsrc cross package also passes, with its selected base providers and native
DocBook tools. All 91 installed payload files check on CM5.
Run `sh tests/xdg-user-dirs.sh /absolute/new-results` on the installed target.
This check passes under a non-root user with a private HOME. It verifies the
Projects/Downloads defaults, paths with spaces, repeated updates and rejection
of invalid inputs without changing the configuration. Allocation-failure
handling and complete desktop integration remain outside this result.

The five upstream C/header files remain unchanged. With the actual AArch64
post-wrapper compile commands, Cppcheck 2.22 reports 64 unchanged diagnostics and GCC 16.2
`-fanalyzer` reports 13. Clang 23.1.3 reports one unchanged potential leak.
The comparison covers all three compiled C units and their unchanged headers.
Both variants use the final config header, base iconv/gettext headers, actual
GCC include-fixed paths and measured AArch64 LP64 macros. No new finding appears.
The leak trace requires an inconsistent `stat(NULL)` success path; it is not
confirmed. Allocation-failure paths need repair and fault-injection tests.
Ports owns these inherited findings. No category is suppressed and no clean
source audit, Valgrind or sanitizer runtime result is claimed.
