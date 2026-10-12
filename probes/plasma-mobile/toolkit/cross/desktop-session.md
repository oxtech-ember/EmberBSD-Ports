# Full KWin dependency migration

The full Wayland KWin 6.7.5 recipe uses the common Qt 6.12, Frameworks 6.31,
GCC 16.2 and Mesa 26 / LLVM 23 stack. KWin's recipe and PLIST originate from
pkgsrc-wip commit `60460008d0c770590e46fc229035b8e454472a80`; copyright and
inherited patch authorship remain intact. Source URLs and SHA256 are recorded
in [sources.tsv](../sources.tsv). This is still an integration candidate:
a full accelerated KWin/Plasma session has not been accepted.

The full Aurorae, Breeze, libkscreen and kscreenlocker 6.7.5 packages pass
normal package checks. KWin's KCMs, screen locker, decorations, global shortcuts
and runner components are retained. Optional KPipeWire, libeis and accessibility
client integration remain absent; remote capture/input is not accepted.
Old GCC 12 compatibility patches and unresolved-symbol suppression are not used.
The two external Wayland demo builds now inherit the parent cross platform,
sysroot, Qt metadata and native scanners. Both demo binaries cross-link successfully.

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

Aurorae's launcher uses `/bin/sh`; it previously embedded the build host's
shell path. Kscreenlocker's emergency-unlock script now embeds target paths
for `ck-list-sessions` and Qt's `qdbus`. Both target files must exist in the
sysroot before configuration. `qdbus` is declared as a QtTools dependency.
The generated script no longer depends on a macOS executable.

## ConsoleKit 2.0 and Polkit

ConsoleKit 2.0 builds as a complete cross package with its X11 helpers, shipped
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
