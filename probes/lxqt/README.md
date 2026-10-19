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

The exporter checks that every overlay file is tracked by Git. It uses the
standard `plasma-mobile` exporter and records the applied recipe inventory.
Include the common cross, graphics, media and toolkit profiles in that order.
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

The same host-tool selection now covers libfm-qt, PCManFM-Qt, globalkeys,
notificationd, runner, themes, the Qt platform plugin and the policy agent.
Their source recipes retain the pinned pkgsrc manifests and patches.
libfm-qt, PCManFM-Qt, themes and the platform plugin pass ordinary package
checks. Other application packages and the installed session remain pending.

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

## Source regressions

The [extended-source analysis](source-analysis.md) records the platform-plugin
and file-manager scopes, inherited findings and parser limitations.

The Wayland qdbus helper uses `/bin/sh`, calls Qt's installed qdbus path and
declares `qt6-qttools` as a runtime dependency. `check-wayland-qdbus.py`
applies the actual package patch to the pinned archive and exercises the
helper with a fake qdbus command under `dash`, which rejects Bash-only
parameter substitution. It checks the `run` branch for `qterminal`,
`pcmanfm-qt` and `lximage-qt`, plus `openmenu`. The data paths include spaces
to check directory splitting and quoting:

```sh
python3 probes/lxqt/check-wayland-qdbus.py \
    /absolute/distfiles/lxqt-wayland-session-0.4.1.tar.xz \
    probes/lxqt/recipes/wayland/lxqt-wayland-session
```

The LXQt CMake finder for `xdg-user-dirs-update` checks a path and does not run
the target program. Cross builds pass the target `/usr/pkg/bin` path and check
that the executable exists in the sysroot. Run the source contract check with
the recipe and target sysroot paths:

```sh
python3 probes/lxqt/check-wayland-target-tool.py \
    probes/lxqt/recipes/wayland/lxqt-wayland-session \
    /absolute/target-sysroot
```

This check does not execute `xdg-user-dirs-update` or start a Wayland session.

The `lxqt-wayland-session-0.4.1nb4` package passes the GCC16 cross build and
pkgsrc package checks. Its archive installs the qdbus helper with a `/bin/sh`
shebang and declares `qt6-qttools` and `xdg-user-dirs` as runtime dependencies.
The configured CMake cache selects `/usr/pkg/bin/xdg-user-dirs-update` from the
target sysroot. The archive SHA256 is
`ffecd1259055f8110d2c33fc33d8e06d0c12e6e66a61cea068404d460872a8e3`.
Installed-session execution and full LXQt runtime closure remain separate
acceptance gates.

The liblxqt backlight helper checks the driver before reading its files.
It accepts one integer from `scanf` and `fscanf` and rejects invalid input.
It releases a previous driver candidate before replacing that candidate.
The driver priority and valid brightness range are unchanged.

Run the regression against a clean original liblxqt archive and the same
source with `patch-backlight-null-driver` applied:

```sh
python3 probes/lxqt/check-backlight.py /absolute/original-liblxqt \
    /absolute/new-baseline-results --baseline
python3 probes/lxqt/check-backlight.py /absolute/patched-liblxqt \
    /absolute/new-port-results
```

The test includes the real source. It uses synthetic files and checks missing
devices, replaced allocation ownership, malformed input and valid boundaries.
It does not access a backlight device. The native run uses ASan and UBSan.
An explicit allocation counter checks the replaced driver strings because
LeakSanitizer is unavailable on the macOS/arm64 host.

Baseline and patched Cppcheck runs use the GCC16 target headers and macros.
The helper's null-driver finding and two GCC `-fanalyzer` ownership findings
are absent after the patch. Clang Static Analyzer checks both the C helper
and its C++ consumer with the target compilation flags. It is analysis-only.
The existing style findings remain visible.
The packaged GCC16 helper also passes the no-device stdin path under an
unprivileged VM user. This check requires an absent `/sys/class/backlight`
and supplies no brightness value. It does not test physical backlight control.

The Qt model uses `Q_MOC_OUTPUT_REVISION=69` from Qt 6.12.
The libqtxdg baseline and patched source have the same unique Cppcheck
diagnostics. Three `strPlusChar` and three `pointerOutOfBounds` reports in
`tst_xdgdirs.cpp` are Qt literal model errors. Qt's `operator""_L1` returns
`QLatin1StringView`; these expressions concatenate strings and `QChar` values.
Clang analysis and the target tests cover these expressions without error.
Cppcheck 2.22 cannot parse the complete expanded Qt system-header configuration;
this separate parser limitation is retained in the analysis receipts.

Two complete libqtxdg upstream test programs pass ten native ASan/UBSan cases
with the existing Qt 6.12 host libraries and common GLib 2.90.1 provider.
Both the library and the test executables use the sanitizer flags.
The native memory run does not cover the directory suite, because Darwin
`QStandardPaths` uses different default directories. The target run covers
all 21 cases.
The native Qt and GLib dependency libraries are not instrumented.
Leak checking remains outside this sanitizer coverage.

The luit recipe declares zlib and the existing common encodings package.
It selects target `locale.alias` and `encodings.dir` paths explicitly.
The configure patch preserves native file checks. In cross mode, the recipe
checks these files in the common sysroot before configuration.

```sh
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-luit-results
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-target-results \
    --ssh ember-test-host
```

All six upstream check modes and two exact-byte encoding conversions pass
with the GCC16 target binary. The same eight cases pass in a native
ASan/UBSan build. Valgrind Memcheck does not support the tested macOS/arm64
host or EmberBSD/aarch64 guest. These sanitizer runs are not Memcheck runs.

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
X11 and Wayland session execution require separate target acceptance.
The Wayland session requires a supported compositor and its own package.
