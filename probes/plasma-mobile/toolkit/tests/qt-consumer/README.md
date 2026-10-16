# Installed Qt Core/Gui/SVG consumer

This AI-assisted EmberBSD check is BSD-2-Clause code and a self-authored SVG
fixture. It checks the common Qt package set without requiring a display.
It does not create an OpenGL context or accept GPU rendering, HDMI or Plasma.

## Build on the development host

Use the verified EmberBSD sysroot, GCC16 cross compiler and matching native
Qt generators described in [the cross workflow](../../cross/README.md).
The installed Qt CMake exports, moc and rcc must work for a real consumer.

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
PKG_CONFIG=/absolute/native/pkgconf sh \
    probes/plasma-mobile/toolkit/tests/qt-consumer/build.sh \
    /absolute/cross-tools /absolute/ember-sysroot \
    /absolute/host-qt/qtbase /absolute/new-build
```

Set `EMBERBSD_CROSS_ARCH=x86_64` for amd64; the default remains AArch64.
The compiler triple must match the selection. The result is an ELF executable
for that CPU. No target program executes on the host. Build objects and receipts stay outside the source checkout.

## Run on EmberBSD

Install the shared Qtbase, SVG and ImageFormats packages and their ordinary
runtime dependencies. Preserve the existing package inventory first. When a
cross-built package has account creation disabled by default, D-Bus needs
`PKG_CREATE_USERGROUP=YES` for the target pkg_add invocation. Its normal package
script creates the service account with `/sbin/nologin`; do not skip scripts or
force unresolved dependencies. `pkg_add -n` rejects absent dependencies rather
than simulating their recursive installation. Check the full local package
closure and archive hashes before installing.

Copy the executable and `run.sh` to the target, then run:

```sh
sh /absolute/run.sh /absolute/qt-consumer /absolute/new-results
```

Each of two fresh processes runs four thread/signal and image lifecycles.
The checks require queued delivery to the application thread, bounded thread
completion, an embedded resource, SVG raster pixels through both the renderer
and image plugin, PNG round-trip pixels, and rejection of invalid/missing images.
SVG, PNG, JP2 and MNG format discovery is required; only SVG/PNG decoding is
exercised. Removing all plugin search paths must return the specific
missing-plugin error. qmake must report the selected Qt version. Live loader
inventory and SHA256 values identify the executable, libraries and plugins.

For package lifecycle acceptance, remove only Qt SVG with ordinary pkg_delete,
confirm the consumer fails because libQt6Svg is absent, reinstall the same
verified package and repeat the check. Do not force deletion of a required
package or remove unrelated dependencies.

## CM5 result, 2026-10-11

Qt 6.12.0 passed on CM5 Rev 1.0 / BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B,
using EMBERV3DRENDER #11 and the previously accepted common GCC16/Mesa26/LLVM23
stack. Carrier PCB and installed UEFI source revisions remain unknown.
The five packages in [the package receipt](../../cross/qt-packages.md) were
installed through ordinary pkg_add. The normal/restart, missing-plugin and
SVG removal/reinstallation checks passed. All 75 live `/usr/pkg` library/plugin
hashes matched the selected build sysroot. Base OS libraries were excluded
from that package-hash comparison.

| Artifact | SHA256 |
| --- | --- |
| Consumer | `6bfcd36eb7abd7272f181ff4ae8121dbc188f49ea5bd0a6d6e4b67c6f69a722b` |
| Qt Core | `05ae52edd83b9579aefbeb5a0e2556aca1ee479b6f67e6c9bb3f2048c0cf9c46` |
| Qt Gui | `974d415804631c637e59cb01e866a97181fed19f9423548ce4173691d598e341` |
| Qt SVG | `474a930303e5f063b2dfee7a2f221c057d3ba81dd289ba10b774226439cec80d` |
| SVG image plugin | `ebf33785707f5087d3d410297c2011c275d8d947db7f022e0f332770e6ec278e` |

GCC 16.2 compiled the consumer with `-Wall -Wextra -Werror` and passed `-fanalyzer`
using the same target compilation command. Cppcheck 2.22 was attempted with
the compilation database and Qt library model, but stopped on Qt's generated
moc revision guard. Target GCC preprocessing then reached an unsupported
C++/target-header parse in assert.h. Neither is a completed Cppcheck pass; no
diagnostic category was suppressed. There is no validated Valgrind execution
path on this EmberBSD/AArch64 target. Memory analysis and full upstream Qt
suites remain separate gates, as do ShaderTools/LanguageServer runtime use,
Quick/Wayland, accelerated Qt rendering and desktop acceptance.
