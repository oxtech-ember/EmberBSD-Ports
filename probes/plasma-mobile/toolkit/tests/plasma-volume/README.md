# Check the Plasma volume provider

`plasma-pa` supplies `org.kde.plasma.private.volume`. Plasma Workspace imports
this module from `applets/notifications/global/PulseAudio.qml`.
The Workspace recipe therefore requires the runtime package.
The provider does not depend on Workspace.

## Inspect the packages on the build host

Build `audio/pulseaudio-qt` and `audio/plasma6-plasma-pa` with the
[current cross workflow](../../cross/README.md). Keep normal package checks.
Use the same committed toolkit export, sysroot and accepted native generators.
The recipes build their upstream tests. Do not run target binaries on the host.

Run the metadata check with the two staged `/usr/pkg` directories:

```sh
BMAKE=/absolute/native/bmake MAKECONF=/absolute/cross/mk.conf \
    ruby probes/plasma-mobile/toolkit/tests/plasma-volume/package.rb \
    /absolute/pkgsrc /absolute/paqt-stage/usr/pkg /absolute/pa-stage/usr/pkg \
    /absolute/verified-distfiles /absolute/packages/All
```

The check reads the verified Workspace archive and evaluates its real recipe.
It requires the runtime dependency, correct PulseAudioQt header metadata,
the staged QML module, an AArch64 ELF plugin and exact archive payloads. It does not execute QML.
A missing dependency, wrong include directory, empty archive or missing plugin must fail.

## Run the upstream validator on a supported host

```sh
CMAKE=/absolute/cmake sh probes/plasma-mobile/toolkit/tests/plasma-volume/host-percent.sh \
    /absolute/verified-distfiles /absolute/new-test-work /absolute/host-qt-prefix
```

This check compiles the original PercentValidator source and upstream test
with Qt 6.12, ASan and UBSan. It does not replace the target package test.
Valgrind Memcheck is not supported on the macOS AArch64 build host.
Run Memcheck on the target tests when a supported execution platform is available.

## Check speaker-test callback ownership

```sh
CMAKE=/absolute/cmake ruby probes/plasma-mobile/toolkit/tests/plasma-volume/host-speaker.rb \
    /absolute/verified-distfiles /absolute/new-test-work /absolute/host-qt-prefix \
    /absolute/audited-canberra-include
```

This regression reads the pinned upstream `speakertest.cpp` and applies the
recipe patch. It keeps the production method and callback bodies unchanged.
Native Qt and the audited `canberra.h` supply real types and API declarations.
Backend doubles select synchronous failures and deferred successful completion.
The unpatched control must leak ownership after all three fallback failures.
The patched body must free that allocation, preserve each successful fallback,
and release callback ownership exactly once. ASan and UBSan check execution.
Explicit allocation counts also work where LeakSanitizer is unavailable.
This check does not validate a real sound backend or device.

## Check the installed target module

Install the complete packages with their runtime dependencies.
Run this probe as the desktop user inside the intended session:

```sh
/usr/pkg/qt6/bin/qml import.qml
```

The probe loads the real plugin and verifies the PulseAudioQt volume constants.
It exits with a failure for an import error or incorrect value.
Also run the cross-built upstream `percentvalidatortest` and `mapstest`.
Copy these executables from their build outputs; do not compile on the board.
Keep their library versions and checksums with the result.

Import success does not establish a working audio device or server.
Notifications, volume changes, feedback sounds and physical output need separate
session checks. The optional Canberra Pulse backend and sound theme are separate
runtime providers; this port does not claim their acceptance.
