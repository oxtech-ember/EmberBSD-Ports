# KWin OpenGL/V3D session check

This check runs the installed KWin Wayland compositor on its virtual backend.
It requires active OpenGL compositing and a V3D renderer.
The existing [Qt Quick consumer](../qt-quick-gpu/README.md) then checks its
scene and layer pixels through the private Wayland session.

## Requirements and use

Install the common KWin, Mesa/V3D, Qt, Frameworks and D-Bus packages.
KWin also needs the common Vulkan loader for Vulkan-Hpp initialization.
Use a user who can open the DRM render node. Root is not required.
The script does not change device permissions, services or installed settings.
Build the Qt Quick consumer on the development host as its README describes.

```sh
sh run.sh /absolute/qt-quick-gpu \
    /absolute/toolkit/tests/qt-quick-gpu/run.sh \
    /absolute/new-results
```

All three arguments must be absolute paths. The output directory must not exist.
Quote paths that contain spaces. The script passes them through environment
variables, not through KWin's session-command parser.

The run uses a private HOME, XDG directories and D-Bus session.
Its 1280×1024 output is virtual; it does not change the monitor mode.
Screen locking is disabled only in this private test session.
KWin exits when the client wrapper exits. The whole session has a 240-second
limit, followed by a five-second kill grace period.
The D-Bus support query has a 15-second limit and a two-second kill grace period.

## Checks and evidence

The script fails if KWin does not report active OpenGL compositing on V3D.
It also fails on a nonzero child result, a compositor failure or timeout,
a changed boot identity, or a Wayland socket left after compositor exit.
The supplied Qt Quick runner must be the linked production `run.sh`.
That runner checks two fresh processes with sixteen scene/layer phases each.
It also requires rejection of wrong pixels, non-Wayland QPA and a missing QML module.
The pixel checks cover 65,536 client pixels in total.

The output preserves `compositor.log`, `supportinformation.txt`, both exit
statuses, boot identity, and the Qt Quick logs under `client/`.
The Qt Quick runner records its executable and loaded-library SHA256 values.
Keep these outputs with the tested board, kernel and package identities.

This is a short virtual-output check. It does not capture compositor output.
It does not accept HDMI/KMS presentation, physical input, PAM unlocking,
a complete Plasma shell, Vulkan rendering, or sustained desktop use.
On 2026-10-13, this public wrapper passed on CM5 under an existing non-root
user with render-node access. See the [hardware receipt](../../cross/cm5-kwin.md).
