# NetBSD framebuffer backend checks

These checks cover the Qt 6.12 `bsdfb` platform plugin and its pure helpers,
including bounded buffering of fragmented wscons records. They use synthetic
framebuffer memory and input events; they do not open device nodes or require a
board.

The backend remains experimental. One target runtime smoke completed on
NetBSD 11/aarch64 with the plugin built from Ports revision
`fce69ff2bf347cda459079f3c0abf60da4a1d6cb` (plugin SHA-256
`3ba999c327d63feb933ff503c757e470d781b9fe6283c8d4d4e806dc5c25062c`). The
framebuffer reported 800x1280 pixels, a 3200-byte stride, and offset 256; the
plugin used 90-degree rotation. The Qt Quick first-frame and home-state checks
passed while Xorg was stopped. The plugin opened the wscons input node, but
physical touch was not tested. A 20-second smoke ended without application
errors. The test process then exited, and the prior Xorg session returned with
the original display mode and device permissions.

This single runtime check does not establish physical touch, cold-boot behavior,
startup performance, GPU acceleration, or compatibility with other devices.

The backend scope is deliberately narrow: NetBSD wsdisplay in dumb framebuffer
mode, a linear 32-bit RGB framebuffer (`Xrgb8888`, or the supported
little-endian `Xbgr8888` ordering), CPU-only software composition, and absolute
wscons pointer events. It supports 0, 90,
180, and 270 degree rotation. By default, `input-coordinates=native` maps
the calibrated axes to framebuffer pixels, then rotates the pointer to match
the display. Select `input-coordinates=logical` for touch axes that already
increase rightward and downward on the mounted screen. For example,
`bsdfb:rotation=90:input-coordinates=logical` scales each axis directly to
the corresponding landscape screen dimension. `preserve=1` keeps the existing contents until
the first frame is presented; `preserve=0` permits the initial clear. Set
`QT_QPA_FB_DISABLE_INPUT=1` to disable wscons input. The plugin does not provide
GPU-accelerated rendering, relative input, or other pixel depths and layouts.

Run the isolated helper checks with a host C++17 compiler and a patched QtBase
source tree:

```sh
cmake -S tests/qt-bsdfb -B /absolute/new-build \
  -DQTBASE_SOURCE_DIR=/absolute/patched/qtbase
cmake --build /absolute/new-build
ctest --test-dir /absolute/new-build --output-on-failure
```

The layout, pointer, and record-buffer tests have no Qt dependency. To enable
the FrameGate, blit, and input-failure tests, set `QT_HOST_PREFIX` to the host
Qt 6.12.0 prefix; CMake then finds only that exact Qt version under its
`lib/cmake` directory.

The separate `build-plugin` wrapper cross-builds only
`QBsdFbIntegrationPlugin` against the patched QtBase tree and the selected
target Qt package. Supply the SDK's target toolchain, target sysroot and native
Qt host tools. This is compile and link evidence only; runtime and hardware
acceptance are separate.
