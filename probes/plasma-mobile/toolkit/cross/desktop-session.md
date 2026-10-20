# Full KWin dependency migration

The full Wayland KWin 6.7.5 recipe uses the common Qt 6.12, Frameworks 6.31,
GCC 16.2 and Mesa 26 / LLVM 23 stack. KWin's recipe and PLIST originate from
pkgsrc-wip commit `60460008d0c770590e46fc229035b8e454472a80`; copyright and
inherited patch authorship remain intact. Source URLs and SHA256 are recorded
in [sources.tsv](../sources.tsv). [KWin now passes OpenGL/V3D virtual-output acceptance on CM5](cm5-kwin.md).
The full Plasma Desktop and physical HDMI session remain unaccepted.

The full Aurorae, Breeze, libkscreen and kscreenlocker 6.7.5 packages pass
normal package checks. KWin's KCMs, screen locker, decorations, global shortcuts
and runner components are retained. Optional KPipeWire, libeis and accessibility
client integration remain absent; remote capture/input is not accepted.
Old GCC 12 compatibility patches and unresolved-symbol suppression are not used.
The two external Wayland demo builds now inherit the parent cross platform,
sysroot, Qt metadata and native scanners. Both demo binaries cross-link successfully.

KWin 6.8 passes the selected `Qt6CoreTools_DIR`, `Qt6GuiTools_DIR` and
`Qt6WaylandScannerTools_DIR` to both external demos. Without these inputs,
ECM can select the target `qtpaths` during configure. Qt can also select the
target `qtwaylandscanner` during protocol generation. Both real demo
configurations and the pip protocol generation target pass with the selected
host tools. Native configuration does not create a cross cache.
This check does not establish a complete KWin package or target execution.

Run the regression in the package's `ALL_ENV` environment.
Use the patched KWin source and its accepted parent CMake cache.
Select a new probe directory in the shared object tree.

```sh
python3 ../tests/kwin-external-cross.py --sdk-source SDK_SOURCE \
  --source KWIN_SOURCE --parent-cache PARENT_BUILD/CMakeCache.txt \
  --cmake CMAKE --work NEW_PROBE_DIRECTORY
```

## Host tools and runtime commands

[Native KPackage](libplasma.md) creates package metadata during the host build.
KAuth uses upstream's explicit code-generator-only mode, with the **Polkit**
backend selected even on macOS:

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja \
HOST_CC=/absolute/cc HOST_CXX=/absolute/c++ JOBS=2 \
  sh build-kauth-tool.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR \
    HOST_COREADDONS NEW_WORK
```

`HOST_COREADDONS` can use the matching prefix produced by
`build-kpackage-tool.sh`. Copy `NEW_WORK/tooling/KF6Auth` into the common
`EMBERBSD_KF6_HOST_TOOLING` directory. The helper produces the exact upstream
`foo.policy` fixture and rejects a missing argument. Target KAuth remains a
complete package with its own policy generator and backend. Its exported
configuration now searches for native tools outside the target sysroot.

KWin's protocol scanner is also a native build tool. Its nested build previously
inherited the target compiler and failed on macOS `-arch`. Build the unchanged
upstream standalone scanner and copy its `bin/qtwaylandscanner_kde` into the
common host-tooling `bin` directory:

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja HOST_CXX=/absolute/c++ \
  sh build-kwin-scanner.sh DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK
```

The recipe uses upstream's explicit `QTWAYLANDSCANNER_KDE_EXECUTABLE` interface.
No board-native compilation or target executable on macOS is required.

The scanner helper selects the exact version from the common `plasma6.mk`,
then requires one matching `x11/plasma6-kwin` source-manifest entry and verifies
its SHA256. It does not keep a separate old scanner version or accept an
archive from another Plasma release. The current 6.8.0 upstream standalone
scanner uses C++20, Qt Core and ECM; its full compositor dependencies are
not required for this private host generator. Use the same native compiler
ABI as the host Qt libraries.

```sh
ruby ../tests/kwin-scanner-source.rb VERIFIED_DISTFILES HOST_QT
```

This regression uses the actual checked KWin archive and host Qt version.
It stops at a recorded native CMake configure boundary and never compiles
the generator. Corrupt archives, duplicate source rows and a mixed shared
Plasma version fail before work-directory creation. It establishes source
selection, not scanner generation, target linking or desktop acceptance.

Aurorae's launcher uses `/bin/sh`; it previously embedded the build host's
shell path. Kscreenlocker's emergency-unlock script now embeds target paths
for `ck-list-sessions` and Qt's `qdbus`. Both target files must exist in the
sysroot before configuration. `qdbus` is declared as a QtTools dependency.
The generated script no longer depends on a macOS executable.

## ConsoleKit 2.0 and Polkit

ConsoleKit 2.0.0nb1 builds as a complete cross package with its X11 helpers, shipped
manual pages and upstream tests. It uses GLib/GDBus directly; the inherited
unused dbus-glib dependency is removed. Upstream's autogen supports absent
gtk-doc, and API HTML is disabled by default in both the original recipe and
this cross build. No runtime component is removed to avoid a host-tool error.

The changed ConsoleKit session IDs require Polkit 127nb4. The compatibility
patch derives from Gleb Popov's [FreeBSD Ports change](https://github.com/freebsd/freebsd-ports/commit/12b84b980b45573c93be5382a274dbe872a1eb73),
with ownership declarations corrected for allocated strings. The complete
Polkit package keeps its daemon, PAM helper, introspection and policy handling.
Deploy the ConsoleKit/Polkit pair together; an older ConsoleKit installation
has not been accepted with the new short-ID database mapping.

[The real-library regression](../tests/consolekit/ids.c) runs on CM5 with a
private D-Bus fixture. The previous installed library fails process-to-session
ID mapping. The patched library passes short-ID lookup, object existence,
legacy full-object-path input and rejection of absent sessions/processes.
Reproduce with `PKG_CONFIG=/absolute/pkg-config sh tests/consolekit/build-ids.sh
CROSS_TOOLS SYSROOT NEW_WORK`, then run `timeout -k 5 60 ./ids` on EmberBSD
with the matching installed libraries and `dbus-daemon` in PATH.
It does not modify or grant privileges through the system D-Bus service.
This bounded result does not prove live seat ownership, user authentication,
lock/unlock or suspend integration. ConsoleKit and the changed Polkit daemon
have not yet received full service acceptance on CM5.

The installed `ck-launch-session` also passes a real-daemon regression on CM5.
The old launcher converted a child's exit code 42 into success, crashed when
no command was provided, and omitted the terminator of the `--service`
parameter list. The Ports patch decodes `waitpid`, retries interrupted waits,
handles fork/wait failure and safely selects the default shell. With the same
real private-bus daemon, the regression fails before and passes after the fix.

Run `sh tests/consolekit/launch-runtime.sh NEW_OUTPUT` on an idle EmberBSD
acceptance board. It requires root and refuses an existing ConsoleKit daemon
or PID file: ConsoleKit's runtime database is global even on a private bus.
The seven checks cover success, exit 42, signal status 143, the default shell,
an explicit service, a missing executable and an unknown option. Child checks
require a real session cookie and resolve it through the daemon, so silently
running outside a session cannot pass. All sessions close afterwards; only the
test daemon's own stale PID file is removed after confirmed process exit.
The test never calls suspend, shutdown or reboot. Root session creation does
not establish ordinary-user login, device ownership, lock/unlock or suspend.
The matching Polkit 127nb4 and KAuth 6.31.0nb1 packages are installed; their full
system-service integration remains unaccepted. All 257 regular payload hashes
match the common sysroot and CM5; package tools check 267 payload files.

ConsoleKit package SHA256:
`5a71430187181ac00bffaad621f866a1af268118c74150f52525a0ea5b3a0f61`.
Launcher results SHA256:
`62e6c4a7b684f1c29b2f52f096e2ee871d33c32e1f641dfd0802b116233b79ab`.
The changed launcher passes GCC 16's analyzer. Cppcheck with the actual target
flags reports the same inherited GLib header warning as the Polkit analysis;
this is not a clean audit of the dependency headers. Valgrind is unavailable.

Cppcheck 2.22 reports no warning/performance/portability findings for this C
fixture with system includes omitted. This is not a clean audit of all GLib,
ConsoleKit or Polkit source. On both changed Polkit units, Cppcheck with
actual GCC predefined macros reports one inherited GLib header warning; it is
not a clean audit. GCC 16's analyzer completes without diagnostics for both
units. Valgrind is unavailable.

## Current kernel boundary

On the CM5 fan kernel, eight shared writable memfd mappings pass: exact and
page-rounded sizes 4095, 4096, 4097 and 1920000 bytes. The old partial-page mmap
workaround is therefore not carried into current KWin. This does not test every
memfd/sealing case or complete compositor rendering. The fan configuration and
kernel remain unchanged.
