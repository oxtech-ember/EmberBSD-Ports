# Plasma Workspace nested shell probe

This experimental profile builds the genuine Plasma Workspace 6.7.5 shell and
selected runtime modules for a private nested Plasma Mobile session. It is not a
complete Plasma desktop, login session, or hardware support claim.

The next consolidated validation baseline is GCC 16.2, Qt 6.12.0 LTS and
KDE Frameworks 6.31. These have not been validated by this recipe yet. The
GCC 12.5 / Qt 6.11.1 / KF 6.26 base results below are diagnostic evidence from the
existing VM, not acceptance of that older stack as the final system baseline.

## Source and patch provenance

`sources.tsv` pins the original KDE archives. Plasma Workspace uses the licenses
preserved in its `LICENSES/` directory and per-file SPDX notices: GPL-2.0-only,
GPL-2.0-or-later, GPL-3.0-only; LGPL-2.0-only, LGPL-2.0-or-later,
LGPL-2.1-only, LGPL-2.1-or-later, LGPL-3.0-only, LGPL-3.0-or-later;
BSD-2-Clause, BSD-3-Clause, MIT, CC0-1.0, and KDE accepted-license references.
No upstream source archive or generated executable belongs in this repository.

The KWin 6.7.5 archive supplies its original `src/virtualkeyboard_dbus.h`
(GPL-2.0-or-later). The Qt `qdbuscpp2xml -A` command reproduces the generator
specified in upstream `src/CMakeLists.txt`; no D-Bus interface is fabricated.

`0001-nested-shell-profile.patch` is a local, AI-assisted change, not submitted
or accepted upstream. It adds an opt-in profile, disabled by default. The normal
upstream build path is retained. This profile selects real upstream CMake targets
and narrows dependency discovery to their actual dependencies. It does not
introduce service stubs or permissive unresolved-symbol linker flags.

The historical Plasma 6.5.2 pkgsrc-2026Q2 package was inspected at commit
`0491f5e57e8fba00998bf1a6c0958ef421fefaa1`:

- `x11/plasma6-plasma-workspace/Makefile`, SHA256
  `094d72a5037c54e691dc2eca454bfcca5ba75ec2490821dd18ca929f6d3ace80`.
- `patches/patch-startkde_config-startplasma.h.cmake`, SHA256
  `1c2f0e8ea37e20a01ef37a1002f068ec603480f4356733d3773bf778ddb1fa63`.

That patch originated in FreeBSD and defines the configured XDG directory for
`startkde`. This profile does not build `startkde`, so it does not apply that patch.
The pkgsrc Makefile marks the full workspace package broken because it needs
`wip/plasma6-kwin`; this probe does not claim that package has been repaired.

## Dependencies and private build

The recorded probe used the existing Qt 6.11.1 and KDE Frameworks 6.26.0
installation with a common Plasma 6.7.5 source build. Do not install a second
Qt/KF stack. The common Plasma
prefix must provide libplasma, KWayland, Plasma Activities, libkscreen,
LayerShellQt, KScreenLocker and KNightTime 6.7.5, plus Plasma Wayland Protocols
1.21 or newer. Installed Frameworks must include `kf6-kdeclarative`,
`kf6-kstatusnotifieritem`, `kf6-ksvg`, and their ordinary dependencies.
Package installation remains a separately coordinated system action.
Build the current Plasma libraries in the common prefix selected by
`PLASMA_PREFIX` (default: `$HOME/.cache/emberbsd-plasma-current/install`).
`build-common-component.sh` builds LayerShellQt, libkscreen, or KScreenLocker
from the pinned 6.7.5 sources with the portability patches described below.
The probe uses NetBSD's `/usr/bin/cc` and `/usr/bin/c++` (GCC 12.5.0), matching
the existing Qt/KF stack's `libstdc++.so.9`. The pkgsrc GCC 15 package instead
links `libstdc++.so.7`; combining these two C++ runtimes is rejected. `CC` and
`CXX` can override the compiler only when its runtime is compatible.

`0002-netbsd-common-libraries.patch` removes only KDE's fatal-linker-warning
flag on NetBSD. Existing `libutil` compatibility aliases emit `.gnu.warning`
messages through the system Qt dependencies. Those warnings remain visible;
`--no-undefined` remains active and unresolved symbols still fail the link.
The Workspace profile applies the same narrowly scoped change.

`0003-libkscreen-cxx23.patch` replaces the unavailable `ranges::to`, `views::zip`,
and `std::format` convenience APIs with an ordered loop and Qt formatting. It
preserves filtering, ordering, mode indices, and two decimal places. The real
`std::expected` API is provided by NetBSD's GCC 12 C++23 library and is retained.
These patches are local, AI-assisted work and have not been submitted upstream.

`0004-kscreenlocker-cxx23.patch` replaces `views::zip` in the PAM conversation
with an indexed traversal of the two equally sized spans. It retains response
references, message order, and the original authentication and error handling.
This is a compiler compatibility patch, not validation of screen locking or PAM.

Both `0003` and `0004` are temporary adaptations for the base GCC 12 standard
library. Once the shared Qt/KF/Plasma toolchain has migrated to GCC 16.2 with a
single compatible C++ runtime, rebuild the original sources without these two
patches and remove them if the native build and runtime checks pass. Installing
a newer compiler alone does not establish runtime compatibility.

The private build passes `prefer-current-prefix.cmake` through
`CMAKE_PROJECT_INCLUDE`. This places current shared headers before `/usr/pkg`
headers, where the older packaged LayerShellQt would otherwise shadow its
6.7.5 replacement despite selecting the new CMake target and shared library.
The helper is specific to validation before migration of the system prefix.

Run as an ordinary user:

```sh
./prepare-sources.sh
JOBS=1 ./build-common-component.sh layer-shell-qt
JOBS=1 ./build-common-component.sh libkscreen
# Requires the current libplasma/PlasmaQuick in the common prefix.
JOBS=1 ./build-common-component.sh kscreenlocker
KWIN_VIRTUALKEYBOARD_XML="$HOME/.cache/emberbsd-plasma-workspace/src/org.kde.kwin.VirtualKeyboard.xml" \
    JOBS=1 ./build-nested-workspace.sh
```

`prepare-sources.sh` requires the `src` path to be absent. It rejects every
existing tree or symlink before touching the sources, verifies each archive
against `sources.tsv`, extracts fresh trees, and applies every patch once.
It never infers complete preparation from individual source-text matches.
For another preparation, select a fresh `WORKSPACE_ROOT` or move the old `src`
aside explicitly; existing archives may be reused after checksum validation.
A failed preparation is retained for inspection and is rejected on a retry.

`WORKSPACE_ROOT` can override the private cache root. The install prefix is its
`prefix` subdirectory. No login manager configuration or existing session is
changed. All build and install logs are kept privately under `logs`.

The profile builds `plasmashell`, workspace/task/notification/MPRIS libraries,
keyboard-layout, containment, sessions, battery, D-Bus and shell QML components,
the system tray, clock QML module, and image/color wallpaper support. It also
installs the original upstream `plasma-applications.menu` and 40 category
`.directory` files through `add_subdirectory(menu)`. With this profile's relative
`SYSCONFDIR=etc`, the menu is in `prefix/etc/xdg/menus` and category data in
`prefix/share/desktop-directories`. The session must include `prefix/etc/xdg`
in `XDG_CONFIG_DIRS`, `prefix/share` in `XDG_DATA_DIRS`, and set
`XDG_MENU_PREFIX=plasma-`, matching upstream `startplasma.cpp`. It does not
build `startplasma`, session shutdown helpers, settings modules, or device
notification services. Upstream session backends keep their real capability
checks and explicit unsupported-operation behavior. Do not set
`PLASMA_SESSION_GUI_TEST` to simulate working session operations.

Further modules such as Plasma NetworkManager, ModemManager, audio volume,
PowerDevil, and Milou are independent requirements of Plasma Mobile. Their absence
must be reported by runtime validation, not replaced by mock QML modules.

For an existing build missing only these menu data, `configure-menu-data.sh`
reads and validates its cached source, private prefix and relative directories,
including ECM's `share/desktop-directories` default for empty cache entries.
It configures a separate `LANGUAGES NONE` driver around the real upstream
`menu` directory, preserving the main source/build tree. Inspect the printed
build directory's `menu/desktop/cmake_install.cmake` destinations, then run
`cmake --install` on that data-only build directory. No build command, compiler
check, replacement menu, or package transaction is involved.
The native data-only installation added exactly 41 upstream files; its manifest
and every installed file matched the source. The existing `plasmashell`, main
CMake cache and Ninja build file kept their digests. This data check does not
by itself validate the Mobile application list.

## Validation

`test-libkscreen.sh` runs the upstream `testscreenconfig` and
`testconfigserializer` executables in private D-Bus sessions. The upstream Fake
backend is used only by those tests; it is not a replacement display backend.
On NetBSD 11/aarch64 with system GCC 12.5.0, Qt 6.11.1 and KF 6.26.0,
the suites passed 10 and 8 cases respectively on 2026-10-06.

LayerShellQt 6.7.5 built, installed, and imported `org.kde.layershell` through
the real Qt QML engine using its offscreen platform. KScreenLocker 6.7.5 built
and installed completely. Their loader checks and libkscreen's loader check
resolved one C++ runtime, `/usr/lib/libstdc++.so.9`. No screen-lock, PAM
authentication, login-manager, or hardware test was performed.

After building Workspace, run `verify-workspace.sh`. It creates fresh XDG
directories with `mktemp` and `umask 077`, clears inherited private D-Bus
addresses, and uses separate private D-Bus sessions. It sets `C.UTF-8` and
`XDG_CURRENT_DESKTOP=KDE`, enables immediate symbol resolution, and requires
exactly one resolved system `libstdc++.so.9`. Each native command has an
external 30-second timeout with a two-second termination grace period.
The verifier requires the exact `plasmashell 6.7.5` version line and both
positive QML success messages. It rejects the `qmlRegisterType requires absolute
URLs` warning and clears inherited Qt logging overrides so diagnostics remain
visible. Each run retains its own logs under the printed `runtime-probe.*/logs`
directory. It imports the selected QML modules, constructs
the task, notification, battery and keyboard-layout models, and requires
the real Clock object to advance through three distinct seconds. These checks
do not establish that a compositor, complete Mobile shell, or device service
works; those require a separate live nested-session check.

Workspace 6.7.5 completed all 644 native Ninja steps and installed on
2026-10-06. The verifier passed: `plasmashell 6.7.5`, all 13 QML imports and the
four model constructors loaded, and Clock advanced through three distinct
seconds. The offscreen models reported zero tasks, zero notifications, no
batteries, and zero keyboard layouts. Those are observed probe values, not
claims about service or hardware support. The strengthened verifier also passed
one native rerun with all positive assertions and the QML warning rejection
enabled. That run retained a missing kqueue watch-path warning, but no invalid
QML registration warning. The initial run additionally recorded a locale
fallback and a changed UPower owner. Source preparation's rejection of an
existing tree was checked locally, including preservation of a sentinel file.
The strict rerun selected KirigamiPlatform from the coordinated shared prefix;
the initial loader log selected its packaged `/usr/pkg` version. This does not
establish migration of the full Frameworks stack. Local mutations of the real
loader log confirmed rejection of an absent, duplicate or wrong C++ runtime and
an unresolved library, while the unmodified native log passed.

The executable was an aarch64 ELF for NetBSD 11.0 with SHA256
`c4739d32a4bdd0f5242ac856fda4c67adcf96aaa12324a02f90ff3b028b43a94`.
Its loader selected current Plasma/PlasmaQuick 7, LayerShellQt 6, KWayland 6,
and Plasma Activities 7 from the shared prefix, with one `libstdc++.so.9`.
The executable digest identifies this private probe build, not a reproducible
binary guarantee across other directory layouts or toolchain versions.
No live compositor or complete Plasma Mobile session was validated by this
recipe before the coordinated toolchain-migration shutdown boundary.
