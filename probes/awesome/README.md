# awesomeWM with system Lua

This experimental source probe builds awesomeWM 4.3 and LGI 0.9.2 on
EmberBSD/NetBSD 11 with the operating system's Lua 5.4.6. It supplies an
X11 window manager with Lua configuration, tiling layouts and widgets.
These are the latest upstream stable releases checked on 2026-10-07;
their old release dates do not imply that pkgsrc selected the versions.

The [source manifest](source.tsv) pins upstream archive hashes.
[Provenance](PROVENANCE.md) identifies upstream compatibility backports,
local changes, licenses and the boundaries of verification.
The probe does not install another Lua or change the active desktop.

## Native dependencies

Use an ordinary account with the base development and X11 sets installed.
The default compiler is `/usr/bin/cc`; the checked environment uses native
GCC 12.5.0, Lua 5.4.6 headers in `/usr/include` and `/usr/lib/liblua.so`.
The system Lua CLI must link libpthread at process startup. EmberBSD's
Lua CLI build fix adds that dependency without changing the Lua version
or shared library. Unmodified NetBSD 11 Lua can load LGI but aborts when
Pango/GLib first creates a worker thread. The builder detects this before
building and requires the corrected system CLI; it does not use a preload
or install another interpreter.
Required build tools are CMake, Ninja, GNU make, pkg-config, curl and
Bash. Documentation generation is disabled,
so AsciiDoctor and LDoc are not required.

Development libraries and pkg-config files must be available for GLib/Gio,
GObject Introspection, libffi, Cairo with XCB, Pango, GdkPixbuf, D-Bus,
libxdg-basedir, startup-notification, libxkbcommon and libxkbcommon-x11.
X11 dependencies include libX11, libxcb, xorgproto, xcb-util,
xcb-util-cursor, xcb-util-keysyms, xcb-util-wm and xcb-util-xrm.
The GLib, GObject, Gio, cairo, Pango, PangoCairo and GdkPixbuf typelibs
must be installed; pkgsrc supplies GLib's typelibs as `glib2-introspection`.

The initial VM inspection found the major graphical libraries and
typelibs installed. libxdg-basedir and xcb-util-xrm were subsequently
installed without replacing shared dependencies.
The builder checks dependencies but does not install packages.
A minimal clean-machine installation has not yet been tested.
No project-owned helper uses Python. The recipe consumes installed GI
typelibs rather than running upstream's Python-based introspection scanner.

## Build and check

Choose a new absolute work path whose parent exists. Paths may contain
only letters, digits, `_`, `.`, `/` and `-`. Work directories are never
reused or removed by the builder. The default `JOBS=1` limits peak memory.

```sh
mkdir -p "$HOME/.cache"
sh build-native.sh "$HOME/.cache/emberbsd-awesome"
```

An optional second argument is an absolute directory containing both
archives named in `source.tsv`. Their hashes are still mandatory.
`CC`, `CFLAGS`, `LDFLAGS` and `JOBS` may be overridden. `CC` is one compiler
executable, not a shell command. Lua remains the system interpreter and
library, independently of compiler selection.

The work directory retains source archives, patched sources, build trees,
logs, a rendering test image and the installation under `install/`.
The build first checks the system Lua header/library ABI. It then tests
LGI enums, Cairo/Pango rendering, GdkPixbuf loading, Gio and coroutine
callbacks using the changed Lua 5.4 resume API. awesome's own LGI check
remains enabled. Finally it checks version output, the generated upstream
configuration and dynamic library resolution.
The system Lua CLI, installed awesome executable and build-time
`lgi-check` must have an ELF `DT_NEEDED` entry for libpthread. `readelf`
checks these direct dependencies, while `ldd` checks library resolution.

The source archive includes 100 theme icons. A restricted native
GdkPixbuf helper generates the 13 missing Zenburn variants, preserving
upstream's gamma, alpha and grayscale operations without installing
ImageMagick. Every generated icon's RGBA pixels are checked against
reference hashes from ImageMagick 7.1.2-32 before the WM build starts.

The historical LGI filename `corelgilua51.so` is an upstream module name.
In this probe it is compiled and linked against Lua 5.4, installed under
`lib/lua/5.4`, and loaded only by the system Lua. The filename does not
indicate an installed Lua 5.1 runtime.

Before running the resulting commands, load their module search paths:

```sh
. "$HOME/.cache/emberbsd-awesome/environment.sh"
awesome --version
awesome --check --config \
    "$HOME/.cache/emberbsd-awesome/install/etc/xdg/awesome/rc.lua"
```

The [shared X11 launcher](../x11-desktops/run-nested.sh) creates a separate
X server, private XDG configuration and D-Bus session. From an X11 desktop:

```sh
sh ../x11-desktops/run-nested.sh awesome \
    "$HOME/.cache/emberbsd-awesome/install" "$HOME/.cache/emberbsd-awesome"
```

Add `--headless` for an off-screen Xvfb session. The launcher supplies the
Lua module environment. `X11_DISPLAY_NUMBER` selects an unused display.
Its [runtime test](../x11-desktops/test-runtime.sh) checks real WM behavior,
two Xterm windows, keyboard input through XTEST, saved text and cleanup:

```sh
sh ../x11-desktops/test-runtime.sh awesome \
    "$HOME/.cache/emberbsd-awesome/install" "$HOME/.cache/emberbsd-awesome"
```

`awesome-client` evaluates Lua in the running WM through its private
D-Bus session. A successful configuration syntax check alone does not
establish a working window manager or keyboard input.

## Validation boundaries

Source checksums, patch application and shell syntax are checked locally.
The native icon helper passes all 13 pixel comparisons on the macOS host;
that host check does not establish NetBSD runtime support.
On 2026-10-07, native LGI compilation, its Cairo/Pango/Gio/coroutine
contract, all 13 icon comparisons, lgi-check and awesome CMake configuration
passed after the system Lua pthread fix. The documentation generator also
passed with an explicit build-only Lua module path. Native compilation and
installation complete in a coordinated build window. The source patches fix
the Lua/LGI version fields and the upstream `WM_S_S0` selection name, and
the unchanged shared X11 test passes WM identity,
fullscreen/restore, two application windows, focus, keyboard input through
XTEST, exact saved text and clean session exit.

This establishes a software X11 session in the AArch64 VM. Physical input,
board support, touch, GPU acceleration, performance and long-run stability
remain unverified. The recipe is not yet an installable pkgsrc package.

The current shared Lua target is 5.5.1. The existing 5.4.6 ABI is a
transition state: upgrading it requires rebuilding EFL, LGI, awesome and
other consumers together, not installing a second permanent Lua.
