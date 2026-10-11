# Installed Qt Wayland/EGL V3D consumer

This consumer uses the common Qt 6.12 Core, Gui and OpenGL packages. Qtbase
already supplies the Wayland client and EGL QPA integration in this release.
It needs an existing compositor and does not start or modify a login session.
The separate Qt Wayland module is not required for this client.

## Build and run

Cross-build on the development host against the verified EmberBSD sysroot
and matching native Qt generators:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf \
sh build.sh /absolute/cross-tools /absolute/sysroot \
    /absolute/host-qt/qtbase /absolute/new-build
```

Install the same common Qt/Mesa/GCC runtime packages on the target. From an
existing Wayland session, preserve its private `XDG_RUNTIME_DIR` and
`WAYLAND_DISPLAY`, then run:

```sh
sh run.sh /absolute/qt-wayland-gl /absolute/new-results
```

The runner starts two fresh processes with a restricted environment. Each
requires the actual Wayland QPA, an EGL-backed OpenGL ES context and a V3D
renderer. It rejects a malformed GLSL shader, renders sixteen changing-color
frames with a shader and vertex buffer, and verifies 1024 framebuffer pixels
per frame before Qt swaps buffers. GL objects are destroyed with the context
current. Two additional processes must reject deliberately wrong expected
pixels and the non-Wayland minimal QPA. Each process has an internal deadline
and an external timeout. The runner records live library paths and file hashes.

A successful run establishes Qt's EGL client rendering and submission. Qt's
`frameSwapped` signal alone does not prove compositor output pixels, KMS
scanout, physical input, HDMI or Plasma. Compositor rendering/output capture
and the complete desktop have separate acceptance gates. Compare the captured
runtime hashes with the selected sysroot before accepting a package combination.

The source cross-compiles on macOS with GCC 16.2 against Qt 6.12.0 and the
common fork sysroot. Cppcheck 2.22 and a real GCC `-fanalyzer` compilation pass.
Target execution passed on CM5 on 2026-10-11, as recorded below. Valgrind is not validated on EmberBSD/AArch64;
these checks do not establish a memory-analysis pass.

Sources: [QOpenGLWindow](https://doc.qt.io/qt-6/qopenglwindow.html),
[Qt native context interfaces](https://doc.qt.io/qt-6/qnativeinterface-qeglcontext.html),
and the [common migration sequence](../../MIGRATION.md).

## CM5 result and isolated compositor

CM5 Rev 1.0 / BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B passed the runner.
Its unchanged experimental `EMBERV3DRENDER #11` kernel comes from fork revision
`78c6715a9496f779c3832b27f771bd865a9cdcdf`; kernel SHA256 is
`e3dd93954fa7fde09e9da0667cb67b7e0c3544e91719be8dfc05e478cd9deea4`.
The four modules remain from that same bundle. UEFI source and carrier revision
are not established. The hardware output is separate from this virtual-output test.

Both Qt and labwc report `V3D 7.1.10.2` and OpenGL ES 3.0 / Mesa 26.2.4.
The common packages are MesaLib 26.2.4nb3, libdrm 2.4.134nb2, LLVM 23.1.2nb1,
Qtbase 6.12.0, GCC 16.2.0nb1, labwc 0.20.2nb2 and wlroots 0.20.2nb4.
Both client processes passed all sixteen frames and the negative checks.
All 59 live package library hashes match the final common sysroot.
The compositor exited and removed its private Wayland socket. This is a short
functional check, not a benchmark or sustained-stability qualification.

For the same isolated headless scenario, install labwc and its normal runtime
dependencies, provide access to the V3D render node, then run:

```sh
sh run-headless.sh /absolute/qt-wayland-gl /absolute/new-session
```

The helper selects `/dev/dri/renderD128`, the GLES2 renderer and one headless
output. It uses private XDG directories and a bounded compositor lifetime.
It does not require seatd, a display manager or a monitor for this scenario.
The user keeps control of the existing desktop. HDMI and input are not tested.

The first plain package installation omitted the XKB rules: libxkbcommon
marked xkeyboard-config as a build dependency. labwc then failed during keymap
setup. `libxkbcommon-1.13.2nb2` now retains those data as a runtime dependency.
The normal package build, ordinary replacement and the same CM5 Qt/V3D session
pass. The [dependency regression](../../../../../profiles/common-graphics/tests/xkb-runtime-dependency.rb)
rejects the original build-only closure and checks the real package metadata.

| Accepted artifact | SHA256 |
| --- | --- |
| Qt Wayland consumer | `6c62485190bc40cbb79e0e2a7073bf5674c5f729e4e095eead21c6529ced6214` |
| libxkbcommon-1.13.2nb2.tgz | `356caf52436fefd8de9194cdfc5cd521582162869c2875db6c2e4e012da7a8e0` |
| xkeyboard-config-2.48nb1.tgz | `be5bd56cd5eeb0b9d26563bb5194d04ad372e35ca208490a7c8e5abfd8e2077b` |

