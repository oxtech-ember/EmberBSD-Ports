# Plasma Desktop virtual-output acceptance

This runner starts the installed Plasma Desktop shell as an ordinary user.
It uses KWin's virtual Wayland backend and requires the V3D OpenGL renderer.
It keeps the user's existing desktop configuration separate.

## Requirements and use

Install the complete common Plasma Desktop, Workspace, KWin and dependency packages.
This includes KActivityManagerD and the common Vulkan loader required by KWin.
Use an existing non-root user with access to the DRM render node.
The runner does not change users, device permissions, services or installed settings.

Keep all files in this directory together. Run this command on the target:

```sh
sh run.sh /absolute/new-results
```

Use a short absolute output path. The output directory must not exist.
The Wayland socket path must fit the operating system's UNIX socket limit.
The run uses private HOME, XDG and D-Bus directories.
It enables the installed system XDG defaults and KDE data paths.
It sets the Qt Wayland QPA and OpenGL RHI backend for this test only.

The virtual output is 1280×1024. It does not set a physical monitor mode.
Screen locking is disabled only in the private compositor session.
The whole session has a 240-second timeout and a five-second kill grace period.
D-Bus calls have five-second timeouts. Image capture has a 15-second timeout.
The shell gets up to 90 seconds to create its default layout.
Each D-Bus timeout adds at most seven seconds to that startup limit.

## Checks and saved evidence

The runner requires all these observations:

- KWin reports active OpenGL compositing on V3D before and after the test.
- The D-Bus shell property is `org.kde.plasma.desktop`.
- The default Folder View and panel exist on the single virtual output.
- The panel models contain Kickoff, Pager, Icons-Only Task Manager,
  System Tray, Digital Clock and Show Desktop.
- An unknown connector is rejected without creating an image.
- A desktop containment capture completes and produces a 320×256 PNG header.
- The shell's own Qt RHI log reports V3D OpenGL and no detected QML load error.
- Six layout queries succeed over a further 30 seconds with the same shell process.
- SIGTERM closes the shell successfully. KWin exits with the session wrapper.
- The boot identity is unchanged and the Wayland socket is removed.

The output saves compositor and shell logs, query results, exit statuses,
executable hashes, the desktop capture and its hash.
The shell cleanup escalates to SIGKILL after five seconds if needed.
That escalation fails the test. It does not count as a clean shutdown.
Keep the output with the tested kernel, firmware and package-set identities.

`desktop.png` captures the desktop containment, not the composited panel.
Inspect it after transfer. Its header check does not assess visual correctness.
Applet model presence does not prove that each applet renders or accepts input.
QML diagnostics are a further gate, not a complete functional check of every applet.

This runner does not start the full `startplasma-wayland` login sequence.
It does not accept HDMI/KMS, a display manager, PAM, physical input, Fcitx input,
audio, network applets, remote desktop or sustained desktop use.
It does not measure memory safety. No Valgrind run is claimed.
Target execution is pending; host checks do not establish Plasma acceptance.

## Verified source interfaces

The commands were checked against the unpacked upstream 6.7.5 sources.
The common recipe fixes the source archive and checksum:
[Desktop](../../recipes/x11/plasma6-plasma-desktop/Makefile),
[Workspace](../../recipes/x11/plasma6-plasma-workspace/Makefile), and
[KWin](../../recipes/x11/plasma6-kwin/Makefile).

- Workspace `shell/main.cpp` defines `--no-respawn` and `--shell-plugin`.
  It handles SIGTERM with `QApplication::quit()`.
- `shell/dbus/org.kde.PlasmaShell.xml` defines the `shell` property,
  `evaluateScript()` and `grabContainmentImage()` on `/PlasmaShell`.
  `shell/shellcorona.cpp` registers that object.
  `KDBusService` uses the `plasmashell` application identity.
- `shell/scripting/scriptengine_v1.cpp` supplies `desktops()` and `panels()`.
  `containment.h`, `widget.h` and `appinterface.cpp` supply the checked properties.
- Desktop `desktoppackage/contents/defaults` selects Folder View and `org.kde.panel`.
  `layout-templates/org.kde.plasma.desktop.defaultPanel/contents/layout.js`
  adds the checked applets. Breeze's default layout loads that template.
- `ShellCorona::grabContainmentImage()` requires the screen and its quick item.
  It sends a delayed reply after `QQuickItemGrabResult::ready` and a successful save.
  This is an internal Plasma API. Recheck it when Workspace changes.
- KWin `src/backends/virtual/virtual_output.cpp` names its first output `Virtual-0`.
  `src/main_wayland.cpp` propagates the `--exit-with-session` child's result.
- Qt 6.12 `src/gui/rhi/qrhi.cpp` enables `qt.rhi.general` through `QSG_INFO`.
  `qrhigles2.cpp` emits the renderer evidence checked by this runner.
- libplasma `src/plasmaquick/appletquickitem.cpp` emits `error when loading applet`.
  The runner rejects that diagnostic instead of accepting the error placeholder.

## Host regression checks

The development host needs Ruby and Node.js for these bounded checks:

```sh
ruby host-test.rb
```

The checks reject invalid output arguments, missing V3D evidence, QML errors,
invalid PNG headers and incomplete layout models.
They execute the real session cleanup after a forced startup failure.
Separate fixtures exercise SIGTERM success and forced SIGKILL failure.
The temporary copy replaces only external graphics commands and the clock.
No target binaries run. These fixtures do not emulate a GPU or Plasma.
All added scripts are EmberBSD code with AI assistance.
