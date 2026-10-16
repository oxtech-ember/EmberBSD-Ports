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
    ruby probes/plasma-mobile/toolkit/tests/plasma-volume/package.rb --target amd64 \
    /absolute/pkgsrc /absolute/paqt-stage/usr/pkg /absolute/pa-stage/usr/pkg \
    /absolute/verified-distfiles /absolute/packages/All
```

The selector accepts `aarch64` and `amd64`. The default remains `aarch64`.
Use the matching cross MAKECONF. The amd64 pkgsrc architecture is `x86_64`.
The check reads the verified Workspace archive and evaluates the three real recipes.
It requires NetBSD 11.0, the selected MACHINE_ARCH, and ELF object format in each
recipe and both package archives. Mixed or duplicate archive target metadata fails.
It requires the runtime dependency, correct PulseAudioQt header metadata,
the staged QML module and exact archive payloads. Both staged and archived plugins
must have a complete ELF64 little-endian header for the selected machine.
It does not execute QML or establish complete ELF dependency closure.
A missing dependency, wrong include directory, empty archive or missing plugin must fail.
The package names remain `pulseaudio-qt-1.9.0.tgz` and `plasma6-plasma-pa-6.8.0.tgz`.
The pinned Workspace source and its checksum remain unchanged.

### Test the host auditor with fixtures

```sh
BMAKE=/absolute/native/bmake PKG_CREATE=/absolute/native/pkg_create \
TARGET_CC=/absolute/x86_64--netbsd-gcc TARGET_SYSROOT=/actual/target/sysroot \
    ruby probes/plasma-mobile/toolkit/tests/plasma-volume/package-targets.rb \
    /absolute/verified-distfiles /absolute/new-receipt
```

The regression uses real native pkgtools archives and real bmake. Its miniature
Makefiles and payloads are fixtures. They are not built Plasma audio packages.
Header-only ELF fixtures test the class, byte order and machine checks.
The optional TARGET_CC/TARGET_SYSROOT pair adds one genuine GCC-built amd64 DSO.
That DSO contains no Qt plugin or audio implementation. No target file is executed.
The runner uses a private temporary pkgdb and never installs a native package.
It retains logs, source hashes and labeled sample archives, then removes its
temporary stages and compiler outputs.

The 32-case run preserves default ARM success and accepts explicit ARM and amd64.
It rejects wrong selectors, mixed recipe or archive metadata, missing plugins,
wrong class/endian/machine, truncated or empty headers, and empty payload archives.
Invalid selector checks use otherwise valid inputs, so positional usage errors
cannot hide a missing target check. The original auditor fails 31 cases.
The corrected auditor passes all 32, including the GCC16 DSO fixture.
These host fixtures do not establish a completed amd64 audio package or runtime.

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
