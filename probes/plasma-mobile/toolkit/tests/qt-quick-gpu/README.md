# Qt Quick V3D acceptance consumer

This consumer passes on physical CM5 with the common Qt 6.12 stack, following the accepted
[Qt Wayland/EGL check](../qt-wayland-gl/README.md). It is not a Plasma shell.
It requires the installed common Qt 6.12 Declarative package and the same
native generators, GCC16, Mesa and EmberBSD sysroot.

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf \
sh build.sh /absolute/cross-tools /absolute/sysroot \
    /absolute/host-qt/qtbase /absolute/new-build
```

Run `run.sh ABSOLUTE_BINARY NEW_RESULTS` from an existing Wayland session,
or use `run-headless.sh ABSOLUTE_BINARY NEW_SESSION` on the configured CM5
with the accepted labwc packages. The latter selects the V3D render node and
private XDG directories. Both scripts retain bounded process lifetimes.

The compiled `Ember.GpuCheck` QML module draws changing background colors and
a green rectangle through a separate Quick layer. The consumer requires an
actual EGL/V3D context in the scene-graph render thread. It captures the Quick
window and checks 1024 scene pixels plus 1024 layer pixels for each of sixteen
phases. The runner repeats the process and requires rejection of deliberately
wrong pixels, the non-Wayland QPA and an absent QML module.

## Accepted CM5 run, 2026-10-12

GCC 16.2 cross-built the installed-package consumer on macOS/arm64. Native
Qt 6.12 generators compiled its QML module and AOT cache. The complete
Declarative package passed normal pkgsrc checks and ordinary target installation.
The AArch64 recipe retains its inherited JIT-disabled policy; this does not
claim a JIT port. The build retains Quick Controls, templates and development tools.

CM5 Rev 1.0 / BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B used the unchanged
`EMBERV3DRENDER #11` kernel from `78c6715a9496f779c3832b27f771bd865a9cdcdf`.
The original UEFI and carrier revisions are unknown. The shared stack was
MesaLib 26.2.4nb3, libdrm 2.4.134nb2, LLVM 23.1.2nb1, labwc 0.20.2nb2,
wlroots 0.20.2nb4 and libxkbcommon 1.13.2nb2.

Both normal processes passed all sixteen phases with renderer `V3D 7.1.10.2`.
The scene-graph thread had an actual EGL context. A total of 65,536 pixels
were checked across the two runs. Wrong pixels exited 3; non-Wayland QPA and
an absent QML module exited 2. The compositor also used V3D and completed the
whole positive/negative session in about 11.5 seconds, removing its socket.
All 75 loaded `/usr/pkg` files matched the common sysroot by SHA256.
This is functional acceptance, not a frame-rate or latency measurement.

Native qmllint, Cppcheck 2.22 using the real compile database, and a complete
GCC `-fanalyzer` object compilation passed. Valgrind has no validated
EmberBSD/AArch64 path. No memory-analysis or upstream Qt-suite pass is claimed.

| Evidence | SHA256 |
| --- | --- |
| Declarative package | `741d97e690647a91b36c5ca08f91d036914340a9db766add278c5c4ba9206911` |
| Consumer ELF | `9eab9f3a606b8c1a66469189a304af1f324fb18ae7c73233f0062b9053e0048e` |
| First process | `3bbbe33ebfedc5ad08373a918402e0a64501d229bcfed054a9924a607147dfe8` |
| Restart | `5235047d9af6fc9640ab06e2bc6af49ca341139dabe6755ae0bc0ac1b33fa7af` |
| Live library inventory | `3e237f73bd45284d57d48067969ed31b9f024caaeebda95ce85ae135214e62b5` |
| Compositor log | `730653ca840d6e455c0696b7a724bfcc1caa2281b0ea7144c9c0f1c790472a30` |

Compositor output capture, HDMI, physical input, the complete Controls module,
KWin, Plasma and a long run remain separate acceptance gates.

## Regression after the fan kernel update, 2026-10-12

The same consumer and runners pass again on the same CM5 after the operator's
completed cooling update. The `EMBERV3DRENDER #0` kernel comes from EmberBSD
`ab6f88f04ca73c6958adb39d0e1c717f629e7901`; its installed SHA256 is
`c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.
MesaLib 26.2.4nb4 and LLVM 23.1.3 are the current common providers.

Both sixteen-phase processes again verify 65,536 scene/layer pixels on V3D.
Wrong-pixel, non-Wayland and missing-module checks reject their inputs.
All 75 loaded package files match the current sysroot by SHA256. The private
compositor exits and removes its socket; the boot identity is unchanged
throughout this run. The result archive SHA256 is
`0d21b5b9451dce6c80ce39b737cf17b6bdd785aacc3b396b488682a33b763a8d`.
This is a short graphics regression, not a cooling, HDMI or Plasma acceptance.

Sources: [QQuickView](https://doc.qt.io/qt-6/qquickview.html),
[QQuickWindow](https://doc.qt.io/qt-6/qquickwindow.html), and
[the migration sequence](../../MIGRATION.md).
