# Installed Plasma session acceptance

Origin: EmberBSD, AI-assisted implementation and source audit.

This test starts the installed `startplasma-wayland` classic session as an
ordinary user. The default backend uses a 1280x1024 virtual output. An explicit
`--backend drm` selects the current native BCM2712 1920x1080 diagnostic policy.
The test requires OpenGL
with the selected hardware renderer, Xwayland, KSMServer, Activities, KDED and Plasma Desktop.
It verifies readiness for 30 seconds and requests normal logout.

Native virtual sessions have completed on CM5. A later repeat established a
Qt 6.12 NetBSD detached-launch defect: KWin can inherit forkfd state without
its SIGCHLD handler. Xwayland then waits for startup-script completion and
ordinary clients stall. The [Qt process regression](../qt-process/README.md)
reproduces this failure independently of graphics. The source patch is in the
common Qtbase recipe. The installed corrected runtime passes the checks below.
The earlier 64 MiB BO-budget failure is separate and has a kernel repair.
Host fixtures test orchestration; they do not execute KDE or Mesa.

## Run on the target

Install the prepared common Qt, Mesa, Plasma Desktop, Plasma Workspace,
KActivityManagerD, KWin, Xwayland and their package dependencies. Install the
common Perl package for the supervisor. Use an existing ordinary account with
read and write access to a DRM render character device. Do not run this test through `sudo`.

Keep this directory next to [plasma-desktop](../plasma-desktop/README.md).
No target compilation is required. Select a new absolute output directory:

```sh
sh ./run.sh /tmp/plasma-session-check
sh ./run.sh --renderer powervr-zink /tmp/plasma-powervr-check
sh ./run.sh --backend drm --renderer v3d /tmp/plasma-drm-check
```

The backend is `virtual` or `drm`. `virtual` remains the default.
The renderer and backend options can appear in either order. Duplicate,
missing and unknown options fail before output creation or session launch.
No arbitrary dimensions or KWin arguments are accepted.

The default renderer profile is `v3d`. The only other profile is
`powervr-zink`. Unknown profiles fail before output creation or session launch.
The runner requires at least one readable and writable `/dev/dri/renderD*`
character device. It rejects symlink nodes. It does not select a fixed node
number, create devices or change permissions. Actual renderer evidence
must still match the selected profile.

The PowerVR profile requires the installed
`/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json`. It sets these values only
inside the clean session environment:

| Variable | Value |
| --- | --- |
| `KWIN_COMPOSE` | `O2ES` |
| `GALLIUM_DRIVER` | `zink` |
| `MESA_LOADER_DRIVER_OVERRIDE` | `zink` |
| `VK_DRIVER_FILES` | `/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json` |
| `PVR_I_WANT_A_BROKEN_VULKAN_DRIVER` | `1` |

The last variable is the explicit upstream experimental PowerVR opt-in.
This profile uses one installed ICD. It does not accept a private library
prefix, library interposition or an inherited driver list. It records the
profile, accessible node and ICD hash. The node record proves access only;
it does not identify the device which KWin selects.
For `drm`, an existing ordinary account also needs read and write access to
at least one nonsymlink `/dev/dri/card*` character device. `primary-node.txt`
records an accessible candidate; it does not prove which device KWin opens.

The runner does not change permissions, create accounts or select DRM devices
through `KWIN_DRM_DEVICES`. It leaves session selection to installed KWin.

KWin 6.8 tries logind, ConsoleKit and then its Noop fallback. The test does not
force that fallback or qualify it as a working seat. A reachable system bus
and device access do not establish login, device leasing or input ownership.

`backend.txt` records the requested backend. `output-policy.txt` records the
checked backend, width and height. DRM uses `--drm` without windowed-size
arguments. It requires one enabled `HDMI-A-1` output at 1920x1080, scale 1 and
60000 mHz. The virtual policy requires `Virtual-0` at 1280x1024 with the same
scale and refresh rate. Both support snapshots must contain the selected
KWin backend and those actual output fields. The Plasma layout script checks
the same geometry, desktop, panel and applet models during readiness.
These are programmatic diagnostics. They do not establish visible pixels,
physical HDMI, input devices or a complete seat implementation.

The V3D profile keeps its existing clean environment and driver selection.
No profile starts GPU, display or NPU diagnostic stages.

The path must contain at most 70 characters. The test creates a private HOME,
XDG directories, temporary directory and D-Bus session. It derives `USER`,
`LOGNAME` and `SHELL` from the existing account. It records the system identity,
boot time, binary hashes, service PIDs, readiness evidence and process status.
`boot.before` and `boot.after` are civil-time context. `boot-time-change.txt`
records whether they differ. A clock correction can change `kern.boottime`
without rebooting. Acceptance requires one uninterrupted runner and guard
process chain to complete with successful statuses. The unique output path
cannot be resumed after a reboot.

Preflight calls `org.freedesktop.DBus.GetId` on the system bus before creating
output or starting the private session. It uses `qdbus --system` in a clean
environment and validates the 32-digit bus ID. The call addresses the bus
daemon itself; it does not activate another system service. A missing or
unresponsive bus fails preflight and reports the original query status.
Start the installed `dbus` rc.d service before retrying. A reachable bus does
not prove that a login or power-management provider is installed.

Preflight requires both `/usr/libexec/ld.elf_so` and `/libexec/ld.elf_so`.
The prepared packages use these interpreter paths. The test records their
links and hashes. It does not create loader aliases. File availability does
not prove that a mixed base and package set has a compatible ABI.

Startup readiness, normal logout and supervisor deadlines use `CLOCK_MONOTONIC`
from the existing Perl `Time::HiRes` dependency. Civil clock steps do not change
these budgets. Query start and end Unix times remain diagnostic evidence;
a backward clock step can put the recorded end before the start.

The main deadline is 240 seconds. Cleanup has a separate 12-second budget,
plus the final bounded inventory and reap checks. Each `ps` call has a
2-second timeout. Each D-Bus call has a 5-second timeout and 2-second kill grace.
A forced kill, inventory failure or remaining marked process fails the test.
Logs remain in the output directory on failure. `queries.tsv` records each
query's start and end Unix time, phase, status, service, object and method.
It excludes payloads and process environments. Readiness preserves the query
status, including timeout status 124. Startup retries retain the existing
deadline; a failed liveness query still fails acceptance immediately.
The controller also prints its final phase and status on failure.
`phases.tsv` records monotonic seconds for controller start, compositor display
availability, complete session readiness, accepted logout and completed stop.
`readiness-seconds.txt` records controller-to-readiness time. This interval
includes display and session startup. It excludes the runner's prerequisite
checks. These marks describe programmatic readiness, not first visible pixels
or a sustained performance benchmark. Existing deadlines remain unchanged.

## Startup and logout contract

The route follows the unpacked KWin and Plasma Workspace 6.8.0 sources:

1. The virtual route uses `kwin_wayland_wrapper --virtual --width 1280 --height
   1024`. The DRM route uses `kwin_wayland_wrapper --drm`. Both add `--xwayland
   --no-lockscreen` and one positional application: `/bin/sh ./environment.sh`.
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
- `org.freedesktop.DBus.Properties.Get` reads `shell` on `org.kde.PlasmaShell` at `/PlasmaShell`.
  `evaluateScript` checks the default desktop, panel and six applet models.
- `org.kde.KWin.supportInformation` at `/KWin`. The renderer must remain OpenGL with the selected hardware profile.

All readiness service owners must remain stable. Xwayland must be a live child
of KWin. KSMServer's source selects Qt's `xcb` backend before it exposes its
D-Bus service. The renderer log must contain evidence from the actual
plasmashell PID, selected through the private bus. V3D values must start
with `V3D `. PowerVR values must contain both `zink` and `PowerVR` in the
same renderer field. Values from the vendor, version, environment or another
log line do not satisfy that check. Every reported renderer value must match.
The checker rejects llvmpipe, lavapipe, softpipe and QPainter. The existing
QML error checks remain mandatory.

The controller rejects the literal Mesa prefix `MESA: error:` in `bus.log`,
`compositor.log` and `plasma-session.log`. It checks readiness, each liveness
pass, the logout boundary and the final stopped-session boundary. The first
matching file, line number and original row remain in the diagnostics.
Missing, unreadable, symlink or nonregular logs fail acceptance. Empty logs
and ordinary warnings are allowed. Renderer identity and the absence of this
known error prefix do not prove successful draw completion or visible pixels.

The supervisor creates a private process group and a random environment marker.
It verifies marker visibility before launching the session. It records PID,
UID and start time, without saving process environments. It checks the marker
and identity again before signalling a detached process. It never uses a
process-name kill. The existing user's other sessions are outside this scope.

An outer error handler always attempts cleanup. If process inventory fails,
it still terminates its known live child and private process group. It reports
failure because it cannot prove cleanup of detached processes without a fresh
inventory. It does not guess their identity or signal an unverified PID.

This test checks only the selected fixed output policy. It does not validate
physical HDMI, arbitrary display modes, input devices,
a display-manager login, screen locking, remote desktop or a long running
session. Run the separate Desktop capture check for pixel evidence. Keep the
hardware acceptance record separate.

## Host controls

Run the renderer controls with Python's standard library and an explicit
[SDK host API1 source](https://github.com/oxtech-ember/EmberBSD-SDK).
Select a new output directory in the shared object area:

```sh
python3 -B ./renderer-host.py --sdk-source /absolute/EmberBSD-SDK \
  --work /absolute/new-renderer-probe
```

These controls execute the actual shell parser, backend and renderer checks,
layout JavaScript, current-output predicates, and clean
environment dispatch. They cover both profiles, the legacy two-argument
checker, mixed renderers, software fallbacks, unrelated text and missing
installed prerequisites. They preserve the guard arguments, return status
and controller lifecycle. Baseline and mutated predicates demonstrate the
cause of rejected or falsely accepted evidence. Target paths are explicit
host doubles. These controls do not execute KDE or establish PowerVR Plasma
acceptance. No C or C++ source changes in this profile update.

Run the existing host tests with native Perl and Ruby:

```sh
PERL=/path/to/native/perl /path/to/native/ruby ./host-test.rb
/path/to/native/ruby ./xauthority-host.rb
/path/to/native/ruby ./diagnostics-host.rb
PERL=/path/to/native/perl /path/to/native/ruby ./clock-host.rb
/path/to/native/ruby ./render-health-host.rb
```

On macOS, do not use Apple's protected system interpreters. SIP hides their
process environments from `ps`. The fixtures cover rejected arguments, exit
status, deadlines, detached children, forced cleanup, inventory failure and
inventory timeout after launch. They keep an unrelated process alive. They
also test full-session readiness and normal logout with explicit protocol
fixtures, and reject a session that is shutting down. The property fixture requires
the exact service, object, interface, and property. It rejects the former method
call and an incorrect property name at that protocol boundary.

The Xauthority checks follow KWin 6.8.0 `src/xwayland/lib/xauthority.cpp`:
`generateXauthorityFile` uses `QStandardPaths::RuntimeLocation`, not `TMPDIR`.
The controller accepts a direct regular file in this session's runtime directory.
Both private directories require current-user ownership and mode 0700.
The file requires current-user ownership and mode 0600. No filename length is assumed.
Symlinks, nested paths, traversal and paths outside the session are rejected.
The checks use the full BSD `stat` mode, including the file type.
The fixture never reads or records a real authentication cookie.

The backend controls include unknown and duplicate options, primary access,
DRM/virtual launch arguments, fixed geometry, and both actual support callers.
Named mutants expose omitted primary access, a virtual launch requested as
DRM, missing backend checks and disabled layout-size assertions. They do not
execute KDE. Host controls alone do not establish the installed target result.

Host result: 33 full-controller controls and 25 focused Xauthority controls pass
on macOS with native Perl 5.44 and Ruby 4.0. The focused test runs the actual
controller block with real BSD `stat` mode formatting. Only a foreign UID is
modeled without changing ownership. The pinned previous runner fails on the
correct KWin runtime path. These are host controls. The scripts pass shell,
Perl and Ruby syntax checks. They do not change C/C++ source.

The unmodified public DRM route from `ab2a05a8` passes on CM5 as UID 1000
with kernel `8c26cd72`. KWin reports V3D and one 1920x1080 DRM output.
Full readiness takes 15.279604 seconds. Thirty seconds of liveness and normal
logout pass with all five statuses zero. All 259 BO allocations are released;
reserved memory returns to 12,500,992 bytes without allocation or owner faults.

A separate diagnostic snapshot maps the complete 8,298,496-byte BO and copies
only its visible 1920x1080 RGB pixels. It contains the wallpaper, panel and an
Fcitx diagnostic window, with 144,494 colors and no black pixels. This does not
qualify physical HDMI, first visible-pixel timing, input, seat ownership,
hotplug or long-duration stability.

The complete installed Qtbase 6.12.0nb2 runtime passes two clean sessions on
CM5 with kernel `ecb7a4258aa2263da18088f7ee0a76233ffce92f`, Mesa 26.2.4nb8,
KWin 6.8.0nb1, Workspace 6.8.0nb3 and Xwayland 24.1.14nb3. Controller start to
full readiness takes 18.408 and 15.661 seconds. Each session keeps the original
five-second query deadline, passes 30 seconds of liveness and completes normal
logout in about two seconds. BO accounting returns to its initial value and
reports no allocation failures. The recorded temperature stays below 58 degrees
Celsius without throttling or undervoltage.

These runs use ordinary installed libraries. They do not use library
interposition, tracing, a private QtCore or larger response deadlines.
The installed Qt process matrix also passes 320 child exits and 16 expected
failed launches. A separate Qt/GLES consumer verifies shader pixels in two
Wayland GPU processes and completes compositor cleanup.

The virtual output does not establish physical HDMI, hotplug, physical input,
a remote desktop or long-duration stability. General CL completion recovery
remains unqualified; short successful samples do not establish the cause of
a non-completing job. Target memory analysis remains unperformed.

The system-bus prerequisite and query diagnostics pass 71 host controls.
The pinned previous runner misses an unavailable system bus and converts a
query timeout to status 1. The new controls reproduce both causes and reject
malformed bus IDs. They retain the exact service, object and method contract.
The native session result above does not qualify physical display output.

The clock controls execute the actual deadline loops and post-guard checks.
They model forward and backward civil clock steps, bounded monotonic expiry,
changed civil boot time and unsuccessful or missing process statuses.
The pinned previous harness reproduces the false expiry, extended wait and
skipped status check. These controls do not execute a target desktop session.

The render-health controls execute the actual predicate and its readiness,
liveness, logout and final acceptance callers. They reproduce the previous
ready false success with Mesa draw/TFU errors, reject unavailable logs and
retain expected warnings. Omitted-call controls detect the missing gates.
These host controls do not qualify successful target rendering.
