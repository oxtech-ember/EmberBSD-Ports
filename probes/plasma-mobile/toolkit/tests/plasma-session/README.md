# Installed Plasma session acceptance

Origin: EmberBSD, AI-assisted implementation and source audit.

This test starts the installed `startplasma-wayland` classic session as an
ordinary user. KWin uses a 1280x1024 virtual output. The test requires OpenGL
with a V3D renderer, Xwayland, KSMServer, Activities, KDED and Plasma Desktop.
It verifies readiness for 30 seconds and requests normal logout.

This is a prepared target test. It has not run on CM5. Host fixtures test
failure handling and orchestration only. They do not execute KDE or Mesa.

## Run on the target

Install the prepared common Qt, Mesa, Plasma Desktop, Plasma Workspace,
KActivityManagerD, KWin, Xwayland and their package dependencies. Install the
common Perl package for the supervisor. Use an existing ordinary account with
access to the V3D render device. Do not run this test through `sudo`.

Keep this directory next to [plasma-desktop](../plasma-desktop/README.md).
No target compilation is required. Select a new absolute output directory:

```sh
sh ./run.sh /tmp/plasma-session-check
```

The path must contain at most 70 characters. The test creates a private HOME,
XDG directories, temporary directory and D-Bus session. It derives `USER`,
`LOGNAME` and `SHELL` from the existing account. It records the system identity,
boot time, binary hashes, service PIDs, readiness evidence and process status.

Preflight requires both `/usr/libexec/ld.elf_so` and `/libexec/ld.elf_so`.
The prepared packages use these interpreter paths. The test records their
links and hashes. It does not create loader aliases. File availability does
not prove that a mixed base and package set has a compatible ABI.

The main deadline is 240 seconds. Cleanup has a separate 12-second budget,
plus the final bounded inventory and reap checks. Each `ps` call has a
2-second timeout. Each D-Bus call has a 5-second timeout and 2-second kill grace.
A forced kill, inventory failure or remaining marked process fails the test.
Logs remain in the output directory on failure.

## Startup and logout contract

The route follows the unpacked KWin and Plasma Workspace 6.8.0 sources:

1. `kwin_wayland_wrapper --virtual --width 1280 --height 1024 --xwayland
   --no-lockscreen` receives one positional application: `/bin/sh ./environment.sh`.
2. KWin passes its actual Wayland socket, X display and Xauthority path to
   that short application. The application writes these three values.
3. The controller waits for `org.kde.KWinWrapper` on the private bus. It checks
   the service PID and the private display files.
4. The controller starts `startplasma-wayland` without arguments.
   Private `startkderc` selects `[General] systemdBoot=false`.
5. Plasma's classic startup uses the existing KWinWrapper service. It starts
   the normal session manager, autostart applications and D-Bus services.
6. The controller calls `org.kde.Shutdown.logout` on `/Shutdown`. It requires
   successful exits from both the wrapper and `startplasma-wayland`.

The source contracts are:

- [KWin main_wayland.cpp](https://invent.kde.org/plasma/kwin/-/blob/v6.8.0/src/main_wayland.cpp):
  the parser accepts positional applications. `startSession()` launches them
  with `processStartupEnvironment()` after Xwayland initialization.
- [KWin wrapper](https://invent.kde.org/plasma/kwin/-/blob/v6.8.0/src/helpers/wayland_wrapper/kwin_wrapper.cpp):
  it forwards KWin arguments and registers `org.kde.KWinWrapper` after its
  D-Bus launch-environment update. It owns the Xauthority file and display sockets.
- [startplasma-wayland.cpp](https://invent.kde.org/plasma/plasma-workspace/-/blob/v6.8.0/startkde/startplasma-wayland.cpp)
  and [startplasma.cpp](https://invent.kde.org/plasma/plasma-workspace/-/blob/v6.8.0/startkde/startplasma.cpp):
  the entry point calls `startPlasmaSession(true)`. Classic startup launches
  `plasma_session` and waits for KWinWrapper and Shutdown service removal.
- [Classic startup](https://invent.kde.org/plasma/plasma-workspace/-/blob/v6.8.0/plasma-session/startup.cpp):
  `StartServiceJob::start()` accepts an already registered wrapper service.
- [Shutdown implementation](https://invent.kde.org/plasma/plasma-workspace/-/blob/v6.8.0/startkde/plasma-shutdown/shutdown.cpp):
  `logout()` selects logout without poweroff. Classic completion quits KSMServer
  and KWin, then removes the Shutdown service.

`--exit-with-session=startplasma-wayland` is not used. That coupling would make
KWin wait for the application that itself waits for KWinWrapper to disappear.
The independent controller preserves both normal exit paths.

## Evidence and cleanup

The controller checks these actual D-Bus interfaces:

- `org.kde.KSMServerInterface.isShuttingDown` and `currentSession` at `/KSMServer`.
- `org.kde.ActivityManager.Activities.CurrentActivity` and `ListActivities` at
  `/ActivityManager/Activities`. The current activity must have a nonzero UUID.
- `org.kde.PlasmaShell.shell` and `evaluateScript` at `/PlasmaShell`.
  The shared Desktop check requires the default desktop, panel and six applet models.
- `org.kde.KWin.supportInformation` at `/KWin`. The renderer must remain OpenGL/V3D.

All readiness service owners must remain stable. Xwayland must be a live child
of KWin. KSMServer's source selects Qt's `xcb` backend before it exposes its
D-Bus service. The renderer log must contain V3D evidence from the actual
plasmashell PID, selected through the private bus.

The supervisor creates a private process group and a random environment marker.
It verifies marker visibility before launching the session. It records PID,
UID and start time, without saving process environments. It checks the marker
and identity again before signalling a detached process. It never uses a
process-name kill. The existing user's other sessions are outside this scope.

An outer error handler always attempts cleanup. If process inventory fails,
it still terminates its known live child and private process group. It reports
failure because it cannot prove cleanup of detached processes without a fresh
inventory. It does not guess their identity or signal an unverified PID.

This test does not validate physical HDMI, display modes, input devices,
a display-manager login, screen locking, remote desktop or a long running
session. Run the separate Desktop capture check for pixel evidence. Keep the
hardware acceptance record separate.

## Host controls

Run the host tests with native Perl and Ruby:

```sh
PERL=/path/to/native/perl /path/to/native/ruby ./host-test.rb
```

On macOS, do not use Apple's protected system interpreters. SIP hides their
process environments from `ps`. The fixtures cover rejected arguments, exit
status, deadlines, detached children, forced cleanup, inventory failure and
inventory timeout after launch. They keep an unrelated process alive. They
also test full-session readiness and normal logout with explicit protocol
fixtures, and reject a session that is shutting down.

Host result: 24 controls passed on macOS with native Perl 5.44 and Ruby 4.0.
The scripts passed shell, Perl and Ruby syntax checks. No C/C++ source changes
are present in this test, so Cppcheck and compiled-code sanitizer coverage do
not apply to this patch. Target execution and target memory analysis remain
unperformed.
