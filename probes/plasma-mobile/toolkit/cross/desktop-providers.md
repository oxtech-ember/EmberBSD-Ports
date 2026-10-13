# Current Plasma Desktop providers

Plasma uses Qt6 and KDE Frameworks. Its shell does not require GTK.
The EmberBSD Desktop recipe selects SDL3, Fcitx5/Qt6 and the core event-sound API.
GTK adapters remain separate choices for applications that use those APIs.
The complete Desktop package and input session remain unaccepted.

## SDL3 game controller settings

SDL3 3.4.18 cross-builds with the common GCC16 and graphics providers.
The normal pkgsrc checks pass. All 99 installed payload entries check on CM5.
The official release archive has SHA256
`9c75cf16330322c217dedd2e0609f1124f1b54b8633e763467b4684d0f4334a3`.
The accepted package has SHA256
`604c0b9ba4c5d50f8ea02ee3171334274c4de0b780f57bac93761495aa2fa2d8`.

The Plasma Desktop 6.7.5 adaptation uses SDL3 instance IDs and gamepad events.
It preserves the controller KCM and handles failed opens, absent OS paths,
button bounds, compact button rows, reopen counts and removed-device lifetime.
The module releases its own SDL subsystem reference. It does not call global
`SDL_Quit`. The production DeviceModel API provides one singleton.

[Build and run the real-source regression](../tests/plasma-gamecontroller-sdl3/README.md).
Ports `6aaadb6` was exported into a clean source tree for acceptance.
On 2026-10-13, both GCC16 and Clang23 UBSan builds pass all eight cases on CM5.
They run under an ordinary user. The normal run takes 62 ms; UBSan takes 47 ms.
The virtual fixture checks actual SDL button, axis and removal dispatch.
A separate case checks production rejection of virtual devices.
The test uses only the common GCC16 `libstdc++.so.7` runtime.

Cppcheck 2.22 cannot parse the actual Qt/target headers in either source variant.
Its direct pass stops in `qtypes.h`; the preprocessed pass stops in `assert.h`.
This is incomplete coverage. No diagnostic category is suppressed.
Clang Static Analyzer 23.1.3 completes all three changed C++ units before and
after the patch with target headers and final build flags. It reports no finding.
The actual compile database records the parameters.
UBSan uses `-fsanitize=undefined -fsanitize-trap=undefined` for the test executable.
Qt and SDL shared libraries are not instrumented. No Valgrind or ASan pass is claimed.
Physical USB/Bluetooth controllers, the KCM UI and the full Desktop are separate gates.

## Event sounds without a mandatory GTK adapter

Libcanberra 0.30nb26 defaults to its core event-sound API.
OSS, GStreamer and Vorbis remain enabled. The configure arguments explicitly
exclude GTK auto-detection. `PKG_OPTIONS.libcanberra=gtk3` selects the optional
GTK3 adapter; the obsolete GTK2 option is rejected.

The [provider regression](../tests/libcanberra-providers.sh) queries actual
native and cross package/consumer metadata. The original recipe fails it.
A clean build from Ports `bdff3c6` passes all normal package checks.
All 32 payload entries check after installation on CM5.
The core `libcanberra.so.0.2.5` is byte-identical to the previous core library.
KNotifications and KNotifyConfig use its core API; their installed dependency
chains load without GTK. No GTK application package is removed by this change.
Package SHA256:
`0e76f908b0efc5fbfd5562a7038f04809fe95fc226f5cf262a36ebfcc163f098`.

This change edits package metadata, not C source. Physical sound playback is
not established by library loading. The explicit GTK3 path passes metadata
checks; its complete package remains unaccepted because its Cairo dependency
was unavailable in the isolated candidate build.

## Qt6 input framework

The recipes select Fcitx5 5.1.23, Fcitx5 Qt 5.1.16 and Configtool 5.1.16.
They retain Wayland, the Qt6 input module and the Frameworks 6 settings module.
See [sources, retained features and checks](../recipes/inputmethod/fcitx5/README.md).
Native/cross metadata and archive/patch checks pass. The transitive Frameworks
chain uses the core libcanberra package and contains no mandatory GTK.

Plasma selects the Fcitx Kimpanel backend provided by Fcitx itself.
`BUILD_KIMPANEL_IBUS=OFF` prevents accidental IBus discovery, including cached
IBus results. The common input panel remains. Its former two IBus helper
executables are not part of the Fcitx-selected package payload.
The added CMake option retains the alternative IBus backend for other profiles.

The core nb5 package cross-builds with all normal checks and passes all 51
[installed core tests on CM5](../recipes/inputmethod/fcitx5/tests/runtime/README.md).
Source regressions repair missing-signature parsing and dropped XKB models/options.
Relocatable CMake exports also restore actual Qt6 consumer configuration.
The Qt6 adapter also cross-packages; 48 files and
[five installed plugin/metadata checks](../recipes/inputmethod/fcitx5-qt/tests/runtime.md) pass on CM5.
Configtool package acceptance, input-method activation and typed input remain part of the [CM5 desktop acceptance](cm5-kwin.md).

The X11 input adapter uses xcb-imdkit 1.0.9 and the common uthash 2.4.0.
The recipe rejects fallback to its bundled uthash 1.8.
A [real-source regression](../recipes/devel/uthash/tests/README.md) reproduces
a null-member access in `HASH_SELECT`; the repaired header passes all 101
upstream tests with ASan/UBSan on macOS arm64. Cppcheck reports 39 findings
before and after, with no new finding. GCC and Clang path analysis retain
the documented test-harness warnings. Both target packages pass normal package checks.
The XCB encoding test exits successfully on CM5; a complete XIM input session remains unaccepted.

## KIO workers and input prerequisites

The KIO Extras 26.08.0nb2 package includes MTP workers and audio thumbnails.
On CM5, package tools check 1684 KIO entries and 28 libmtp entries.
The three new plugins resolve their dynamic dependencies.
This does not test a physical MTP device or generated thumbnails.
Poppler keeps its GLib binding and introspection data; GLib does not require GTK.
KDSoap and its discovery client have cross packages, but the SMB worker still
needs a working Samba/talloc cross build. The first PipeWire recipe lacks
an EmberBSD SPA event backend. Screencasting remains unavailable.

The input dependency packages use UnitTest++ 2.0.0, nlohmann-json 3.12.0nb2
and the current 2026.02.25 English Hunspell dictionary data.
UnitTest++ passes all 264 upstream cases on CM5 under an ordinary user.
Two unchanged upstream JSON iterator/access cases pass 295 assertions there.
The JSON binary uses the installed common header package and GCC16 runtime.
These runs are not the full JSON corpus or a memory-analysis result.

[Groff 1.24.2](../../../../profiles/common-build-tools/recipes/textproc/groff/README.md)
provides native HTML manual generation for Enchant cross builds.
Its C23 prototype repair preserves the System V math-error contract.
The recipe keeps manual pages and selects the native helper directory through
pkgsrc's tool symlink. No obsolete Groff compiler mode is selected.

Enchant 2.8.21nb1 preserves its Hunspell provider and generated HTML manuals.
The [target test runner](../recipes/textproc/enchant2/README.md) reproduces the
upstream test-library layout. It uses byte-identical production libraries.
On CM5, the clean `7b73f5a` source and `06ec401` runner pass all 434 main tests
in 52.10 seconds and all 25 Hunspell tests in 0.37 seconds.
The provider test discovers the real module automatically; an empty run fails.
The unchanged main executable first failed with an incomplete transferred
fixture. Restoring the upstream library location fixed that harness error.
Fatal GLib diagnostics remain enabled. These target runs are not memory-analysis passes.

The shared gettext-tools recipe keeps target localization and `autopoint`'s
XZ runtime dependency. Native `msgfmt`, `msgmerge` and XZ remain build tools.
The focused checks pass all 14 Fcitx release catalogs and translated metadata.
Gettext-tools 1.0nb2 and gettext-lib 1.0 cross-build with the repaired common
Libtool dispatcher. Normal package checks, including ELF PIE and RELRO, pass.
On CM5, all 282 package entries check. The
[installed runtime gate](../../../../profiles/common-build-tools/tests/gettext-runtime/README.md)
passes 24 unchanged gettext tests, two autopoint CLI checks and the original
Fcitx translation function with its Russian catalog. The original autopoint
archive test skips explicitly because Autoconf is not installed.
This is 27 PASS, one SKIP and zero failures under an ordinary user.
These short runs do not establish a full Fcitx package, graphical input session
or a memory-analysis pass.

XZ 5.8.4nb1 keeps the native configure shell separate from installed scripts.
The [cross regression](../../../../profiles/common-build-tools/tests/xz-target-shell.sh)
checks the real upstream macro, four templates and pkgsrc's interpreter check.
All 14 target script names use `/bin/sh`; native discovery remains unchanged.
A clean cross package from `ef30b38` passes every normal package check.
On CM5, all 316 files check; compression, decoding, comparison and compressed
text search pass under an ordinary user. Package SHA256:
`3d9425d47be93018158ea6b7817f2118ac2186fd7552f33f64c8fc9cebf2beb4`.
