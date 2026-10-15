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
sh run.sh /absolute/new-results /absolute/capture-pixels
```

Use a short absolute output path. The output directory must not exist.
The Wayland socket path must fit the operating system's UNIX socket limit.
The run uses private HOME, XDG and D-Bus directories.
It enables the installed system XDG defaults and KDE data paths.
It sets the Qt Wayland QPA and OpenGL RHI backend for this test only.

The virtual output is 1280×1024. It does not set a physical monitor mode.
Screen locking is disabled only in the private compositor session.
The whole session has a 240-second timeout and a five-second kill grace period.
D-Bus layout queries have five-second timeouts and two-second kill grace periods.
The shell shares a 90-second startup deadline between layout creation and capture.
A layout query can finish after this deadline; capture does not get a new deadline.
Image capture retries while startup time remains because Quick items can become ready after their models.
Each attempt uses at most 15 seconds, capped by the remaining startup time, plus a two-second kill grace period.

## Checks and saved evidence

The runner requires all these observations:

- KWin reports active OpenGL compositing on V3D before and after the test.
- The D-Bus shell property is `org.kde.plasma.desktop`.
- The default Folder View and panel exist on the single virtual output.
- The panel models contain Kickoff, Pager, Icons-Only Task Manager,
  System Tray, Digital Clock and Show Desktop.
- An unknown connector is rejected without creating an image.
- A desktop containment capture contains visible, nonuniform pixels in a decoded 320×256 PNG.
- The shell's own Qt RHI log reports V3D OpenGL and no detected QML load error.
- Six layout queries succeed over a further 30 seconds with the same shell process.
- SIGTERM closes the shell successfully. KWin exits with the session wrapper.
- The boot identity is unchanged and the Wayland socket is removed.

The output saves compositor and shell logs, query results, exit statuses,
executable hashes, the desktop capture and its hash.
Each capture attempt keeps separate request output, errors, exit status, timeout and PNG-check logs.
Only a successful request with a fully decoded, nonuniform image becomes `desktop.png`.
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

The shell API, default layout and output name were rechecked against the
unpacked upstream Workspace, Desktop and KWin 6.8.0 sources.
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
Capture fixtures require recovery after a cold request failure and rejection when the shared deadline expires.
They check shrinking timeouts, separate image paths, retained errors and child cleanup.
The temporary copy replaces external graphics commands, the clock and liveness sleeps.
No target binaries run. These fixtures do not emulate a GPU or Plasma.
All added scripts are EmberBSD code with AI assistance.

## Decode the capture

Build `capture-pixels.c` with the common cross compiler and target libpng.
Link `-lpng16` and use the target `/usr/pkg/lib` runtime search path.
Pass this binary as the second argument to `run.sh`.
The host contract is `capture-pixels-test.rb NEW_OUTPUT`; use `CPPFLAGS`, `CFLAGS`,
and `LDFLAGS` for the host libpng and optional ASan/UBSan.
The contract accepts opaque color variation and monochrome content with alpha.
It rejects full transparency, uniform black and white images, wrong dimensions,
a truncated header-only file, and corrupted compressed data.

The test creates a digital clock in its private desktop containment.
An empty Folder View can produce a valid fully transparent image.
The decoder requires at least 256 nearly opaque pixels and visible color or alpha contrast.
It checks composition on black and white backgrounds to accept monochrome glyphs.
This proves visible containment content, not a composited panel or HDMI output.
It does not replace manual image inspection or input acceptance.
