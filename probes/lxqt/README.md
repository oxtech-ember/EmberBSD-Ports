# LXQt 2.4 on the common Qt6 profile

The target is [LXQt 2.4.0](https://lxqt-project.org/release/2026/04/20/release-lxqt-2-4-0/),
released on 20 April 2026. The pinned pkgsrc already supplies this release,
including panel 2.4.1, PCManFM-Qt 2.4.1 and Wayland session 0.4.1.
This probe retains one common GCC16, Qt 6.12 and KDE Frameworks 6.31 stack.

## Source and package ownership

The recipes under `recipes/` derive from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Original RCS identifiers,
licenses, source checksums, manifests and portability patches are retained.
The local adaptation separates native generators from target libraries.
It retains the target plugin paths and fixes the backlight helper defects
described below.
It is AI-assisted EmberBSD work and has not been submitted upstream.

Prepare a fresh common profile with the tracked LXQt overlay:

```sh
python3 probes/lxqt/prepare-pkgsrc.py /absolute/new-pkgsrc-export
```

The script checks that every overlay file is tracked by Git. It runs the
standard export, copies the overlay files and records the applied recipe
inventory. The standard export does not include the Plasma toolkit probe.
Include the common cross, graphics and media configuration in that order.
Use the shared EmberBSD sysroot and GCC16 toolchain.
Build ordinary packages with `bmake package`.
Install dependencies with ordinary package tools before building consumers.

## Native generators

LXQt CMake and translation modules need matching host Qt tools.
They do not require another target Qt or another native Qt library build.
Prepare these modules from the verified original archive:

```sh
python3 probes/lxqt/build-host-tools.py \
    /absolute/distfiles/lxqt-build-tools-2.4.0.tar.xz \
    /absolute/common-host-qt /absolute/new-lxqt-host-work \
    --cmake /absolute/cmake --ninja /absolute/ninja
```

Set `EMBERBSD_LXQT_HOST_TOOLS` to the printed staged prefix.
Set `EMBERBSD_QT_HOST_PATH` to the existing matching native Qt prefix.
The cross recipes select its `Qt6LinguistTools` export explicitly.
The generated LXQt configuration retains the target `/usr/pkg` paths.
Native pkgsrc builds retain their original `TOOL_DEPENDS` behavior.

The panel also needs the native Qt Wayland protocol generator. Build its
matching host-only module with
`probes/plasma-mobile/toolkit/cross/build-qtwaylandscanner.sh` and set
`EMBERBSD_QT_WAYLAND_HOST_PATH` to that recipe's installed prefix. The panel
selects the prefix's `Qt6WaylandScannerTools` CMake export explicitly; this
prevents CMake from trying to execute `qtwaylandscanner` from the target
sysroot. Native pkgsrc builds keep their upstream tool dependency.

The `lxqt-panel-2.4.1nb3` cross package passes ordinary GCC16 pkgsrc checks.
Its archive SHA256 is
`0317669ca0c9a1a07631afa274b6b100f17e440e0c42b3240a1b57ec047e101d`.
The package metadata and resolved sysroot dependency records contain no GTK
packages. Its `libstatgrab` dependency uses target Perl 5.44.0 at runtime.
Build-time scanner selection and native-mode dependency retention pass
`check-lxqt-panel-host-tools.py`. Installed-panel execution and a full LXQt
session remain separate acceptance steps.

The same host-tool selection now covers libfm-qt, PCManFM-Qt, globalkeys,
notificationd, runner, themes, the Qt platform plugin and the policy agent.
Their source recipes retain the pinned pkgsrc manifests and patches.
libfm-qt, PCManFM-Qt, themes and the platform plugin pass ordinary package
checks. Other application packages and the installed session remain pending.

The qtermwidget 2.4.0nb3 overlay selects matching staged LXQt and Qt host
tools only in cross mode; native builds retain the pkgsrc tool dependencies.
Its manifest includes the three historical color-schema files. The ordinary
GCC16 build passes all 93 steps and pkgsrc checks. The archive SHA256 is
`40a4d1dfd556b5c54ed84248a26f363c3a4129fa7a291e69a6effe04f0e753f7`. Its
runtime dependencies are `gcc16>=16.2.0nb1` and `qt6-qtbase>=6.12.0nb3`. No
GTK dependency is present.

The qterminal 2.4.0nb4 overlay selects matching host Qt LinguistTools in
cross mode and retains the native pkgsrc tool dependencies. Its three source
patches remove undefined Qxt copy operations, guard empty terminal navigation
and initialize the tab-switcher index. The ordinary GCC16 package build passes
all pkgsrc checks. Its SHA256 is
`f535d1cb7e4d814fa321963950737d21515327c1082e0d63098b1a92e5b6c887`. Runtime
dependencies resolve to the existing qtermwidget 2.4.0nb3 and Qt 6.12 package
set. No GTK dependency is present. Target installation and execution remain
separate acceptance steps.

The PCManFM dependency recipes select upstream libfm 1.4.1 and menu-cache
1.1.1. The source archives match the hashes in the official LXDE release
inventory. Their download URLs pin that inventory's Git commit. Only the
upstream `--with-extra-only` libfm component is selected; this library uses
GLib and retains its LGPL 2.1 license. It does not build the GTK file manager.
Both libraries pass ordinary GCC16 package checks and installed-payload audits.
They retain 12 and 10 payload files, respectively.

The menu-data 2.4.0nb3 package passes the ordinary GCC16 cross profile checks.
It has no compiled source or Qt library dependency. Its CMake project selects
only the desktop YAML translator from the matching native LXQt modules.
`check-menu-data.py` compares all five source menu files and all 25 translated
directory files with the package. All 30 comparisons and 30 changed-byte
refusals pass. The package SHA256 is
`5091730bcb57800079bd7244aa3914a39586a0665be2e7c90e1b8c52ac282d99`.
This checks packaged data. Installed menu selection and the full session remain
separate acceptance steps.

libqtxdg also selects the target icon-engine directory explicitly. A native
`qtpaths --query QT_INSTALL_PLUGINS` returns the host path during cross builds.
The ordinary target package must retain `/usr/pkg/qt6/plugins/iconengines`.
Its upstream tests are compiled with `BUILD_TESTS=ON`; execution remains separate.
The directory tests use the same package prefix as `xdgdirs.cpp`.

The platform plugin also accepts an explicit `QT_PLUGINS_DIR`. The cross recipe
sets it to `${PREFIX}/qt6/plugins`. Native builds retain the real Qt query and
reject a missing directory. `check-qtplugin-path.py` exercises the actual source
path block and the retained LXQt query function. Its eight cases reproduce the
host-path error, check the cross override and retain query failure checks.
The ordinary GCC16 `lxqt-qtplugin-2.4.0nb4.tgz` archive has one payload file:
`qt6/plugins/platformthemes/libqtlxqt.so`, below the package `/usr/pkg` prefix.
Its SHA256 is
`24ac939a47a0d443253d46b8b96426e35168ec762ea29b909dc0063255100b03`.
The CMake install manifest and script select this same target path. The ELF
contains target library search paths and no host Qt path. All 103 registered
runtime dependencies resolve without GTK2, GTK3, Qt4 or Qt5. The ordinary
sysroot installation verifies the file hash, sole owner and `pkg_admin check`.
The preserved `+BUILD_INFO` records build provenance; it is not installed
payload. Plugin loading, normal target removal/reinstallation and a complete
session remain separate acceptance gates.

libfm-qt exports its public GLib, menu-cache and XCB requirements through a
PkgConfig imported target. Its installed CMake config resolves these interfaces
in the consumer build. It retains public headers and avoids exporting build
host or fixed dependency paths. PCManFM-Qt is the target consumer regression.
The buildlink API requires revision 5 for this CMake interface and selects
`pkg-config` as a native tool. The ABI floor remains revision 2 because the
SONAME and all 1,634 public ELF symbols are unchanged.
The tested libfm-qt 2.4.0nb5 archive SHA256 is
`765a8925ec8b7f0e71b36596b5e820995a7cffffc90f51187ab60b77ae3061d6`.
All 158 installed files match the archive and their sole owner.
The real PCManFM-Qt 2.4.1nb3 consumer passes configuration, all 84 build steps
and ordinary package checks against this installed export. Its archive SHA256
is `3f61ac713ac2eb7dbb242cb7a9c9f0526697a65a1dd34168391048d4846ec804`.
Its 62 installed payload files and `pkg_admin check` pass.

The [session policy](session-policy.md) selects a GTK-free Wayland default.
Its revision-7 package retains real lock and idle consumers. The policy
records the remaining closure, X11 and installed-session acceptance gates.

GLib, GObject and GIO are private implementation dependencies of the shared
libqtxdg library. Its public headers contain Qt and libqtxdg types.
The CMake export keeps these libraries out of `INTERFACE_LINK_LIBRARIES`.
This prevents Ninja from searching the build host for `/usr/pkg/lib/libglib-2.0.so`
before a compiler wrapper can map the path. The real qtxdg-tools consumer
reproduces the original failure and builds after this change. Both libqtxdg
DSOs retain the same bytes, exported symbols, SONAME and `DT_NEEDED` entries.

The current LayerShellQt package exports `LayerShellQt::Interface`.
The leave dialog uses this target and requires LayerShellQt 6.8.
The EmberBSD session package retains the upstream device monitor by default.
It uses the common `devel/libudev-bsd` interface. The Linux-only
`sysutils/libudev` package is not the NetBSD provider.
Device event delivery still needs separate drvctl/ndevd runtime acceptance.

The helper verifies the original archive before extraction and refuses an
existing output directory. It preserves configure, build and install logs.
On macOS/arm64 it passes with the common Qt 6.12 host tools.

The terminal closure retains xterm 412 and current luit 20260907. xterm needs
the native `tbl` generator to prepare its complete manual. Use an existing
current groff `tbl`, or prepare it from the common source and patches:

```sh
python3 probes/lxqt/build-tbl.py /absolute/distfiles/groff-1.24.2.tar.gz \
    /absolute/new-native-tbl-work --make /absolute/gmake
```

Set `TOOLS_PLATFORM.tbl` to the printed executable. This builds the original
upstream generator and all its required generated headers. It does not change
the target groff options or install another target provider.

The native cross-libtool recipe keeps compiler selection in the consumer's
wrapper `PATH`. This lets pkgsrc map buildlink paths during shared linking.
Both compiler tags and `LTCC` retain the selected GCC16 tool names.
The causal libXpm rebuild passes the ordinary RPATH and work-directory checks.

## Source checks

The [source analysis and helper regressions](source-analysis.md) record source
coverage, inherited findings, parser limits and runtime helper checks,
including the lxqt-panel compilation database comparison.

## Acceptance boundary

The ordinary common GCC16 package build passes all pkgsrc checks for
libqtxdg 4.4.0nb5, liblxqt 2.4.0nb3, qtxdg-tools 4.4.0nb2 and
lxqt-session 2.4.0nb5. These packages are installed in the shared cross sysroot.
The three real libqtxdg test
programs pass 21 cases on an unprivileged EmberBSD/aarch64 VM with the
offscreen Qt platform plugin. The tested DSO and test programs come from the
ordinary libqtxdg package build. A negative control runs the prefixed directory
test against the original library and reports the three expected directory
mismatches. The matching package library passes all 21 cases.

The VM component run uses an application runtime bundle from the same common
sysroot. It does not establish complete package installation or a desktop
session. The packaged qtxdg-mat executable also passes its version and help
controls under the unprivileged user.
The packaged session, configuration and leave executables also pass six
version/help controls. Their CLI run uses unavailable private D-Bus addresses
and starts no event loop or autostart program. It proves library loading and
application construction only.

Prepared host modules are a build prerequisite. Compilation and component
tests do not establish power control, input or rendering.
The qtermwidget archive build passes on the macOS cross host. The host
`pkg_add` correctly refuses to install a NetBSD package into a Darwin package
database. The qterminal archive also passes the ordinary GCC16 package checks;
target installation and runtime execution remain pending for both packages.
X11 and Wayland session execution require separate target acceptance.
The Wayland session requires a supported compositor and its own package.
