# Plasma Mobile on EmberBSD

Target: Plasma Mobile, KWin and Workspace **6.7.5**, the stable upstream
release on 2026-10-06. Porting and runtime verification are in progress;
this directory does not yet establish a running mobile session.

Use the supported upstream stack, not the age of the binary package
catalog, to choose versions. KDE 4/Qt 4 have been removed from the test VM
and their old installation example has been retired. Existing Qt 6.11.1
and KF6 6.26.0 meet the Plasma 6.7 minimums. They describe the initial
portability probe, not the final system baseline. The coordinated rebuild
targets GCC 16.2, Qt 6.12.0 LTS and KDE Frameworks 6.31.0 with one C++ runtime.
Qt 6.12 was [released on September 30, 2026](https://www.qt.io/blog/qt-6.12-released).

The [common toolkit source candidate](toolkit/README.md) now exports Qt 6.12
and Frameworks 6.31 over the existing common build-tools profile. Its source,
patch and selection checks are separate from native packages and PLIST
acceptance. The [migration sequence](toolkit/MIGRATION.md) preserves one
runtime closure; current Mesa and FFmpeg package integration is still required.

`sources.sha256` pins original upstream archives. The Plasma hashes were
checked against KDE's official `.sha256` responses before recording them.
Keep archives, extracted sources, build products and logs outside Git.
The current component recipes and their order are described in
[BUILDING.md](BUILDING.md), [Workspace](workspace/README.md), and
[D-Bus clients](clients/README.md), plus [KWin](kwin/README.md).
They remain diagnostic build probes.

## Local changes

- `patches/plasma-mobile/0001-optional-screen-recording.patch` adds an
  explicit build option for the PipeWire screen-recording quick setting.
  Default upstream behavior is preserved. A build with this option off
  does not provide screen recording.
- `patches/plasma-mobile/0002-explicit-qml-module-helper.patch` imports
  `ECMQmlModule` explicitly. Without screen recording, configuration reached
  the Waydroid client module without a definition of `ecm_add_qml_module`.
  The helper must not depend on an optional package's transitive imports.
- `patches/plasma-mobile/0003-optional-privileged-helpers.patch` allows the
  private diagnostic profile to omit Waydroid and flashlight KAuth helpers.
  Their UI and D-Bus clients remain genuine upstream components; privileged
  operations are unavailable in this profile. The default remains enabled.
  The installed KF6Auth exports system policy and helper paths, so enabling
  them would escape the private installation or reference the wrong helper.
- `patches/plasma-mobile/0004-discovered-libudev-target.patch` links both
  flashlight targets to the imported target supplied by `FindLibudev`.
  A bare `udev` lost the discovered library directory and failed to link
  on NetBSD; the real library and its include path are retained.
- `patches/powerdevil/0001-battery-monitor-client-profile.patch` builds the
  original battery-monitor D-Bus QML client independently of the power
  management daemon. It does not simulate batteries or power management.

These are local EmberBSD changes, prepared with AI assistance. They have
not been submitted to or accepted by KDE. Upstream SPDX notices and
licenses remain in the original source distributions.

## Toolchain boundary

The selected native compiler must use the same C++ runtime as Qt/KF.
The tested pkgsrc GCC 15 emits dependencies on `libstdc++.so.7`, while
NetBSD 11 Qt/KF use the base `libstdc++.so.9`. Mixing both is rejected.
Current source portability checks use the base GCC 12.5 C++ runtime.
Temporary STL compatibility patches must be retested for removal when the
common GCC 16 toolchain and its dependent Qt/KF libraries are ready. Updating
the compiler alone is not a compatible migration.

NetBSD's existing `libutil` compatibility aliases produce GNU linker
warnings through Qt's dependencies. The component helper keeps those
warnings visible and leaves KDE's `--no-undefined` check enabled.
Runtime validation must also confirm that only one C++ runtime is loaded.
`sh tests/check-kwin-loader.sh` regresses the launcher gate for the selected
libinput, missing libraries and mixed C++ runtimes. The same-SONAME input
fallback was observed in the native KWin build's loader closure.

The nested launcher reuses the Enlightenment process-scope helper with a
separate `EMBERBSD_PLASMA_SESSION` marker. Its original marker remains the
default. Run `sh scripts/test-process-marker.sh /absolute/new/test-directory`
as an ordinary NetBSD user to check both markers: orphan and TERM-resistant
children, cancellation, fresh enumeration, and preservation of unrelated
processes. These native regressions passed; a full Plasma session lifecycle
still requires the runtime checks below.

## Component checks

`sh scripts/check-imports.sh /absolute/build/root` checks real Plasma,
Nano, battery, volume and Breeze QML constructors in a fresh private D-Bus/XDG
profile. It also checks the keyboard/settings versions and immediate
symbol resolution. It does not establish a Wayland session.

The test exposed a partially installed Kirigami tree: Plasma's style-only
directory shadowed the packaged controls, producing empty component URLs
even though the QML process returned zero. Installing the complete Kirigami
6.30.0 module in the same selected prefix fixed this failure. The checker
rejects those registration warnings explicitly. The regression passed on
2026-10-06; offscreen platform, event-filter thread and mapped-cache fallback
warnings remained visible. No claim about those warnings being fixed is made.

KWin 6.7.5 built and ran a real nested Qt Wayland window with QPainter.
The input test delivered `emberbsd` through XTest, KWin and Wayland; owned
processes and sockets were cleaned up. Its NetBSD memfd workaround preserves
logical buffer lengths and seals while reserving the last physical page.
The [KWin recipe](kwin/README.md) records the OS regression, eight seal
checks, source provenance and the condition for removing that workaround.

Plasma Mobile 6.7.5 itself compiled and installed on 2026-10-06 with the
diagnostic helper. The build tree used 115 MiB. Its actual installation
manifest stayed inside the common prefix; 37 installed ELF files passed
immediate loader checks with one base C++ runtime and no missing libraries.
This does not establish the mobile runtime workflow below.

`sh scripts/check-mobile-configuration.sh BUILD_ROOT` exercises the installed
Mobile envmanager in a fresh D-Bus/XDG profile. Its virtual-keyboard default
is immutable: reading it succeeds, while rewriting it returns 2. The launcher
checks the real default instead of repeating that write and aborting startup.

`kactivitymanagerd` 6.7.5 now builds and activates on the private session bus;
without it, `plasmashell` refused to load the Mobile shell. Its nine installed
ELF files passed the same single-runtime loader gate. The original Workspace
menu data and `XDG_MENU_PREFIX=plasma-` restore KDE's application catalog;
`kbuildsycoca6 --menutest` finds Kate, Konsole, Dolphin and Plasma Settings.

The QPainter session creates one desktop and two panels and reacts to a real
pointer click on the app-drawer button. Its application grid stays invisible:
upstream sets the grid's opacity to zero and renders it through
`FlickableOpacityGradient`/`OpacityMask`. [Qt's software backend](https://doc.qt.io/qt-6.11/qtquick-visualcanvas-adaptations-software.html) cannot render
those shader effects. The app catalog and a responsive partial screen do not
establish a usable Mobile session.

KGlobalAccelD 6.7.5 builds with `WITH_X11=OFF`; both installed ELF files pass
the loader gate. KWin's shortcut-enabled configuration succeeds but schedules
611 C++ compilations. That rebuild is reserved for the coordinated GCC 16 /
Qt 6.12 / KF6 6.31 migration. The currently installed diagnostic KWin still
has shortcuts disabled. No shortcut or task-switcher runtime is claimed.

## Required runtime result

A real isolated Wayland session must display the mobile shell, open an
application, switch windows, accept on-screen keyboard input, exit and
restart. Compilation or a QML import alone is insufficient. Phone display,
touch, suspend, battery, modem, native KMS and GPU acceleration need their
own hardware checks.

The stock mobile switcher requires OpenGL compositing in KWin and the
OpenGL Qt Quick backend for live window thumbnails. QPainter can validate
the basic window/input route, but cannot satisfy this mobile workflow.
The integration target is native KMS with one compatible EGL/GL ABI;
working Mesa software rendering is sufficient. Nested X11 OpenGL also
requires DRI3. These graphics requirements remain unverified for this port.

Sources: [Plasma 6.7.5 release](https://kde.org/announcements/plasma/6/6.7.5/)
and [official source archives](https://download.kde.org/stable/plasma/6.7.5/).
