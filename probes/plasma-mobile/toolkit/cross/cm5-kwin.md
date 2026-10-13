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

KWin nb2 declares the common `vulkan-loader>=1.4.357.0` runtime dependency.
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

## Hardware check

Run [the KWin/V3D check](../tests/kwin-v3d/README.md) on the installed board.
It creates an isolated 1280x1024 virtual output and private HOME/XDG/D-Bus state.
The existing Qt Quick consumer checks two fresh processes, sixteen phases each.
Each phase checks 1024 scene pixels and 1024 layer pixels.
Wrong pixels, an absent QML module and a non-Wayland platform must fail.

The 2026-10-13 CM5 Rev 1.0 / BCM2712 D0 / 4 GiB check reports:

- KWin 6.7.5, active OpenGL compositing, renderer `V3D 7.1.10.2`.
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

## Remaining desktop boundary

Plasma Workspace 6.7.5 installs on CM5, with all 7856 KWin/Workspace payload
files accepted by `pkg_admin check`. Under the working Wayland compositor,
`plasmashell --help` succeeds. A normal launch exits with
`starting invalid corona "org.kde.plasma.desktop"`.
The separate Plasma Desktop shell package is absent from this target closure.
Workspace executables alone do not provide a complete desktop session.

The toolkit now prepares the separate Plasma Desktop 6.7.5 recipe.
Its official archive SHA256 is
`079fcf6b87d7bf65e3f2a4670d605fac9469344c279a285a98ad549332d7b53e`.
Native and cross metadata select the common Frameworks and KDocTools providers.
The source candidate retains the inherited tablet and X11 input KCM limits;
Wayland mouse and touchpad backends keep their upstream defaults.
The full package, staged PLIST, source analysis and desktop runtime remain unaccepted.
The build closure still needs QQC2 Desktop Style, current xdg-user-dirs, SDL2
and IBus. Copying the shell QML alone cannot supply its compiled plugins.

The monitor path has a separate limitation. An HP L1950 connected through an
HDMI-to-VGA adapter supplies an EDID extension with 1080p. The installed
2025-06-13 boot firmware selects 1920x1080; the monitor reports an unsupported
mode. Its native panel size is 1280x1024. A bounded `hdmi_max_pixel_freq` test
did not change the selected mode; the original configuration was restored.
The current kernel retains the firmware framebuffer. Native BCM2712 HDMI KMS
mode setting is not provided by the render-only V3D driver.
The virtual output size does not change this physical signal.

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
This build uses the common libiconv/gettext packages. Native and cross recipe
metadata pass; integrated pkgsrc packaging and target runtime remain pending.

The five upstream C/header files remain unchanged. With the actual AArch64
compile database, Cppcheck 2.22 reports 67 unchanged diagnostics and GCC 16.2
`-fanalyzer` reports 14. Clang 21 reports one unchanged potential leak.
The leak trace requires an inconsistent `stat(NULL)` success path; it is not
confirmed. Allocation-failure paths need repair and fault-injection tests.
Ports owns these inherited findings. No category is suppressed and no clean
source audit, Valgrind or sanitizer runtime result is claimed.
