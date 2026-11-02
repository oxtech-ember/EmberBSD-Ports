# labwc 0.20.2 cross package

The ordinary macOS cross build produced and installed `labwc-0.20.2nb2`
into the private EmberBSD AArch64 sysroot on 2026-10-09. The package and
its dependency closure passed inspection. The separate [session check](labwc-session.md)
now passes EGL surfaces, screencopy pixels and USB input in two VirGL VM sessions.

The `labwc-0.20.2nb2` recipe targets the shared wlroots 0.20.2,
Mesa 26, LLVM 23, GLib 2.90.1 and librsvg 2.63.4 stack. It retains the
compositor, labnag, terminal/session helpers, SVG window decorations,
freedesktop icons, translations, configuration examples and man pages.
EmberBSD Ports owns the recipe and cross-build checks. A working desktop
session is checked by the linked bounded VM scenario.

The upstream [0.20.2 release](https://github.com/labwc/labwc/releases/tag/0.20.2)
was current on 2026-10-09. Its
[archive](https://github.com/labwc/labwc/archive/0.20.2.tar.gz) has SHA256
`fae023b6fe022f7057556707a17cdb2d98e0138c5dffaedaa1dade975699f9e8`.
It also matches the pinned pkgsrc SHA512 and size. The recipe is imported
from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`, preserving its
authors and three existing patches. EmberBSD's changes are AI-assisted and
have not been submitted upstream.

## Build selection

Use the [common graphics cross profile](profile.md), accepted
[Wayland scanner](wayland.md), [wlroots package](wlroots-package.md),
[text dependencies](labwc-dependencies.md), [desktop support](desktop-support.md)
and current [librsvg package](librsvg.md). Reuse their installed providers;
this recipe does not need a second compiler, GLib or graphics stack.
Keep the [sysroot provenance](../../common-build-tools/cross/sysroot.md)
with the build. A successful package does not certify the entire base sysroot.

Upstream requires wlroots >=0.20.1 and <0.21.0, Wayland >=1.22.90,
wayland-protocols >=1.39 and, for the enabled input backend, libinput >=1.26.
The common stack supplies the accepted libopeninput 1.31.3 implementation
of that API. The recipe requires wlroots 0.20.2nb4 or newer within the
selected upstream range.

The current accepted wlroots DRM/GLES2 configuration has no Xwayland.
Select this matching Wayland-only variant explicitly in private MAKECONF:

```make
PKG_OPTIONS.labwc= -xwayland
```

The public recipe still suggests the `xwayland` option. Selecting it requires
Xwayland, xcb-util-wm and a wlroots provider built with Xwayland support.
Missing providers fail configuration. This avoids upstream's silent fallback
from its automatic Xwayland setting. X11 application migration remains a
separate stage and is not established by the Wayland-only package.

SVG, icons, labnag, native-language support and man pages are required.
A small upstream Meson correction makes an explicitly enabled SVG feature
fail when librsvg is absent. The explicit disabled SVG path remains valid.
Subproject fallback downloads are disabled. The existing systemd-session
feature remains automatic; EmberBSD does not provide systemd.

Cross builds use the accepted host scanner and its verified installation
receipt. Native scdoc and msgfmt produce the man pages and translations.
Target executables are not build generators. The native recipe does not
inherit these cross tool paths. Build with a new work directory, an external
temporary directory and the ordinary pkgsrc targets:

```sh
bmake -C /path/to/exported-pkgsrc/wayland/labwc \
  MAKECONF=/path/to/private/mk.conf package install
```

The standard cross installation destination is the private sysroot.
It does not install or start a compositor on a VM or physical board.

## Focused checks

Run from `profiles/common-graphics` with new absolute work directories:

```sh
ruby tests/labwc-cross.rb /path/to/labwc-0.20.2.tar.gz \
  /path/to/native-prefix /path/to/new-feature-check
BMAKE=/path/to/native-prefix/bin/bmake ruby tests/labwc-options.rb \
  /path/to/exported-pkgsrc /path/to/private/mk.conf /path/to/new-options-check
ruby tests/labwc-package.rb --rpath-regression
ruby tests/labwc-package.rb /path/to/labwc-0.20.2nb2.tgz \
  /path/to/sysroot /path/to/cross-tools/bin/aarch64--netbsd-readelf \
  /path/to/built/labwc-0.20.2 /path/to/new-package-check
```

The feature regression checks the archive and patch hashes, applies the
patches without fuzz, reproduces the original silent SVG omission and
checks the corrected enabled/disabled behavior with actual Meson.
The option check evaluates the actual pkgsrc recipe for native and cross
builds, including both Xwayland selections and missing-scanner rejection.
The package check compares every installed payload file with the archive,
checks the configured features and inspects the target ELF dependency closure.
Static ELF inspection does not prove which providers a target process loads.

The source/feature and recipe-option checks passed with the rebuilt host
tools. Package inspection matched all 62 installed files/links and inspected
80 AArch64 ELF files. It checks the exact wlroots SONAME, which has no extra
ABI suffix. The RPATH regression allows the accepted GCC/Mesa/LLVM inherited
paths only for those providers and rejects host paths and consumer leaks.
The shared exporter and source registry include this labwc overlay.
Export preflight requires its source pin, feature options, session helper
and all four patches. Exporting the recipe does not establish a working session.

## Package acceptance and remaining session

The first configuration failed because librsvg's `Requires.private` named
its AVIF dependency dav1d without exposing it through buildlink. The conditional
librsvg buildlink correction resolves this in a fresh work directory. The
successful build reused the accepted target libraries; it did not rebuild
librsvg or dav1d and did not add a private pkg-config search path.

Ordinary `configure`, `package` and private-sysroot `install` passed with GCC16,
Meson 1.12.1 and native Wayland scanner 1.26.0. pkgsrc passed its PLIST, file,
permission, PIE, RELRO, runtime search path and work-reference checks.
The package keeps the compositor, labnag, helpers, six man pages, translations,
configuration examples, SVG and icon support. Xwayland is explicitly disabled.
The shared exporter passed 107 refusal checks and full composition across
all six profiles, including source pins, required patches and temporary cleanup.

Package SHA256:
`1632b0d72d9090f8ada1b5643b203256c4e12590e6e41c07706b1fe0da166aa2`.
This records one build, not a bit-reproducibility claim.

The normal upstream test option remains disabled. These package checks do not
start a compositor. [Target session acceptance](labwc-session.md) separately
covers EGL, screencopy, USB keyboard window shortcuts, mouse dragging
and clean repeated sessions on VirGL/Metal.
Physical GPU support and complete SDK provenance remain unaccepted.
