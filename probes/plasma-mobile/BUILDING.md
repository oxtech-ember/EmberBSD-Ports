# Rebuilding the diagnostic components

These recipes capture the native portability work. They are not a completed
Plasma Mobile installer. Read the component results and limitations in
[README.md](README.md) before using the session launcher.

Use an ordinary user on EmberBSD/NetBSD 11/aarch64. The initial probe used
base GCC 12.5, Qt 6.11.1 and KF6 6.26, with current ECM/Kirigami 6.30 in the
common prefix. It must be superseded by the coordinated GCC 16.2,
Qt 6.12/KF6 6.31 rebuild. Do not point `CC` at a different compiler while
retaining incompatible Qt/KF shared libraries.

Prerequisites include CMake, Ninja, pkg-config, D-Bus tools, curl, patch,
gettext, Qt development tools and matching Qt modules: Base, Declarative,
SVG, Wayland, Sensors, VirtualKeyboard and Qt5Compat. KF6 development
packages must include the components requested by each upstream CMake
file, including Kirigami, KDeclarative, KRunner, KCMUtils, KSvg, Prison,
QuickCharts and StatusNotifierItem. Kirigami Addons and QCoro are separate
dependencies. System Wayland protocols, X11/XCB, EGL/OpenGL, PulseAudio,
libcanberra and GLib development files are also required. Missing packages
are reported by the upstream configuration; the helpers do not install them.
Upstream Qt/KDE/GLib build steps use the existing Python interpreter.

## Common sources and prefix

Run from this directory. Select a new absolute build root:

```sh
export PLASMA_BUILD_ROOT="$HOME/.cache/emberbsd-plasma-current"
export PLASMA_PREFIX="$PLASMA_BUILD_ROOT/install"
sh scripts/prepare-sources.sh "$PLASMA_BUILD_ROOT"
```

Preparation refuses an existing work directory, verifies every archive
against `sources.sha256`, and applies the local Mobile and PowerDevil
patches. It does not reuse an ambiguously patched source tree.

The common helper builds and installs one component at a time, preserving
configure/build/install logs under the private build root. Use `JOBS=1`
on a shared four-core/four-GiB guest unless capacity has been coordinated.
Its `CC`/`CXX` overrides are for a coherent replacement toolchain only.

Build ECM, complete Kirigami, Plasma Activities and Activities Stats first:

```sh
JOBS=1 sh scripts/build-component.sh extra-cmake-modules-6.30.0
JOBS=1 sh scripts/build-component.sh kirigami-6.30.0
JOBS=1 sh scripts/build-component.sh plasma-activities-6.7.5
JOBS=1 sh scripts/build-component.sh plasma-activities-stats-6.7.5
JOBS=1 sh scripts/build-component.sh kactivitymanagerd-6.7.5
JOBS=1 sh scripts/build-component.sh kglobalacceld-6.7.5 -DWITH_X11=OFF
```

The Activities library does not provide its daemon. `plasmashell` refuses to
load a shell without the real `kactivitymanagerd` service. Configuration alone
can be inspected with `CONFIGURE_ONLY=1` before allocating a build slot.
`KGlobalAccelD` is also required inside KWin: Mobile's task-panel button calls
the compositor's real `Mobile Task Switcher` shortcut over D-Bus.
The Wayland compositor uses its own input backend, so this library does not
need the standalone daemon's X11 plugin.

Both daemons compiled and installed in the native diagnostic prefix. KWin's
shortcut-enabled configuration was checked, but its 611-object rebuild is
reserved for the common GCC 16 / Qt 6.12 / KF6 6.31 migration. The installed
diagnostic KWin still uses the earlier profile with shortcuts disabled.

Build the matching Plasma Wayland Protocols, KDecoration, KNightTime
and KWayland common libraries from the [KWin recipe](kwin/README.md):

```sh
export BUILD_ROOT="$HOME/.cache/emberbsd-plasma-kwin"
export ARCHIVE_DIR="$PLASMA_BUILD_ROOT/archives"
JOBS=1 sh kwin/scripts/build-kwin-dependencies.sh
```

All current Plasma libraries share `PLASMA_PREFIX`;
do not add a second Qt or C++ runtime to satisfy an individual component.

```sh
JOBS=1 sh scripts/build-component.sh libplasma-6.7.5
JOBS=1 sh scripts/build-component.sh pulseaudio-qt-1.9.0
JOBS=1 sh scripts/build-component.sh powerdevil-6.7.5 \
    -DBUILD_BATTERYMONITOR_PLUGIN_ONLY=ON
JOBS=1 sh scripts/build-component.sh plasma-nano-6.7.5
JOBS=1 sh scripts/build-component.sh plasma-pa-6.7.5
JOBS=1 sh scripts/build-component.sh plasma-keyboard-6.7.5
JOBS=1 sh scripts/build-component.sh qqc2-breeze-style-6.7.5
JOBS=1 sh scripts/build-component.sh milou-6.7.5
JOBS=1 sh scripts/build-component.sh kde-cli-tools-6.7.5 -DWITH_X11=OFF
JOBS=1 sh scripts/build-component.sh plasma-settings-26.08.1
sh scripts/check-imports.sh "$PLASMA_BUILD_ROOT"
```

The PowerDevil option installs only its real battery-monitor QML client.
It does not install a power-management daemon. The complete Kirigami module
is necessary: a Plasma style-only directory can shadow system Kirigami
and leave its controls unavailable.

## Workspace and service clients

Follow [workspace/README.md](workspace/README.md) for LayerShellQt,
libkscreen, KScreenLocker and the genuine Workspace shell/modules. Its
generated virtual-keyboard interface comes from the matching original
KWin source. Workspace has a private install prefix and uses the same
common `PLASMA_PREFIX`. Its short verifier is separate from a live session.

Follow [clients/README.md](clients/README.md) for MMQt, NMQt, BluezQt,
QtKeychain, provider data and plasma-nm. Its `MM_PREFIX` prerequisite is
the real ModemManager client built by the existing
[Phosh recipe](../phosh/client-libs/README.md); it is not
a replacement daemon. Keep the clients prefix in downstream
`CMAKE_PREFIX_PATH` and its pkg-config directory in `PKG_CONFIG_PATH`.

Build KWin with the validated input prefix, then run its separate native
portability and window/input checks as described in its README:

```sh
export LIBINPUT_PREFIX=/absolute/path/to/validated/libopeninput/install
JOBS=1 sh kwin/scripts/build-kwin-6.7.5.sh
```

The final Mobile configuration requires installed matching KWin and
Workspace CMake exports. Set the actual component locations:

```sh
export KWIN_PREFIX="$BUILD_ROOT/install"
export WORKSPACE_PREFIX="$HOME/.cache/emberbsd-plasma-workspace/prefix"
export CLIENTS_PREFIX="$HOME/.cache/emberbsd-plasma-support/prefix"
export MOBILE_BUILD_DIR=/absolute/path/to/plasma-mobile-build
CONFIGURE_ONLY=1 sh scripts/build-mobile.sh
# Start only when the machine has an available build budget:
JOBS=1 sh scripts/build-mobile.sh
```

The helper disables screen recording until the real PipeWire component
is available. It also omits privileged Waydroid/flashlight helpers and their
system D-Bus/polkit registration. These functions require separate OS and
device integration; their clients are not replaced by stubs. Both upstream
options remain enabled by default outside this diagnostic profile. Native
configuration passed with all required dependencies on 2026-10-06 after
adding the explicit ECMQmlModule import. Compilation and private-prefix
installation then passed after using the discovered libudev target.
The build tree used 115 MiB. All 37 installed ELF modules/executables checked
with immediate loader resolution used one base C++ runtime and had no missing
libraries. The Mobile runtime workflow remains unverified.

## Session boundary

`run-nested.sh WORK_DIRECTORY [--headless]` is an unvalidated integration
launcher. `WORK_DIRECTORY/prefixes.txt` lists the selected component
prefixes, one absolute path per line, lowest priority first. A normal run
uses an owned Xephyr on the existing X desktop; `--headless` uses Xvfb.
Each run has fresh XDG directories and its own D-Bus session. It preserves
the account HOME and does not configure a login manager.

Set `LIBINPUT_PREFIX` to the validated libopeninput installation. The
launcher puts its library directory first and checks KWin's actual loader
closure before starting X. Linking against that prefix is insufficient:
without this runtime selection, NetBSD can load the packaged libinput with
the same SONAME and missing KWin-required symbols. The gate also rejects
unresolved dependencies and multiple C++ runtimes.

The launcher reproduces Mobile's upstream environment and applies its
real envmanager inside the private bus before starting KWin. It selects
the installed `plasma-keyboard` executable explicitly. Its cleanup marker
is separate from the Enlightenment session marker; the native process
scope tests are documented in the main README.

For pointer diagnostics, compile `tests/nested-pointer.c` with the base C
compiler, X11/XTest headers and libraries. It accepts `DISPLAY X Y` for a
click or `DISPLAY X Y END_X END_Y` for a drag. It refuses a display unless
exactly one visible top-level window occupies 480×800 at the origin.
Use only the launcher's owned display, and confirm each result from the
real application state or a captured frame; successful event delivery
alone does not prove that the UI handled it.

Default `PLASMA_COMPOSITOR=O2` requests OpenGL. This requires a compatible
graphics stack and, for nested X11, working DRI3. Plain Xvfb does not supply
that contract. `PLASMA_COMPOSITOR=Q` is limited to diagnostic QPainter
tests and cannot validate the stock mobile switcher. A real native KMS
session remains the integration target. Do not call either launch mode
validated until the complete runtime criteria in README have passed.
