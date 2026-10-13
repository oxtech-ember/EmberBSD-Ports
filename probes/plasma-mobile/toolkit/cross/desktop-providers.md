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

The source candidates select Fcitx5 5.1.23, Fcitx5 Qt 5.1.16 and Configtool 5.1.16.
They retain Wayland, the Qt6 input module and the Frameworks 6 settings module.
See [sources, retained features and checks](../recipes/inputmethod/fcitx5/README.md).
Native/cross metadata and archive/patch checks pass. The transitive Frameworks
chain uses the core libcanberra package and contains no mandatory GTK.

Plasma selects the Fcitx Kimpanel backend provided by Fcitx itself.
`BUILD_KIMPANEL_IBUS=OFF` prevents accidental IBus discovery, including cached
IBus results. The common input panel remains. Its former two IBus helper
executables are not part of the Fcitx-selected package payload.
The added CMake option retains the alternative IBus backend for other profiles.

Source selection and a working native dictionary generator do not establish
complete target packages, input-method activation or typed input in Plasma.
Those checks remain part of the [CM5 desktop acceptance](cm5-kwin.md).
