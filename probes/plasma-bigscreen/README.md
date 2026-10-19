# Plasma Bigscreen 6.8 source port

[Plasma Bigscreen](https://plasma-bigscreen.org/get/) is released as part of
KDE Plasma. The target is Plasma 6.8.0, released on 14 October 2026.
The original archive SHA256 in `sources.tsv` matches KDE's `.sha256` response.
The common target providers remain Qt 6.12, Frameworks 6.31 and GCC16.

The complete upstream source requires Qt WebEngineCore and WebEngineQuick,
BluezQt and the KDE Connect QML module. These requirements remain enabled.
The common sysroot currently has no accepted providers for these components.
Source configuration and a component link test do not establish a complete
Bigscreen package or an interactive session.

[Dependency source candidates](DEPENDENCIES.md) retain the pinned pkgsrc
WebEngine NetBSD patches and prepare the current BluezQt D-Bus client.
Their source checks pass. Ordinary GCC16 builds, packages and native
Bluetooth service support remain pending. The WebEngine source release is
versioned independently from the selected common Qt ABI.

BluezQt 6.31.0 rejects `NetBSD` through ECM and its `metainfo.yaml` platform
contract. Its client API requires a running BlueZ 5 D-Bus service. The Linux
rfkill implementation also uses `/dev/rfkill` and Linux event structures.
A native Bluetooth service adapter and radio-state backend require separate
work. Setting `KF_IGNORE_PLATFORM_CHECK` does not provide these contracts.

The local `inputhandler` CMake patch uses ECM's `Inotify::Inotify` provider.
Linux supplies this API through libc. EmberBSD supplies a separate library.
The patch preserves the actual upstream device watcher and gamepad handling.
It is AI-assisted EmberBSD work and has not been submitted upstream.

The keycode/evdev declarations belong to the common `devel/input-headers`
provider, as in KWayland. They do not establish Linux device ioctl support
on EmberBSD. The existing serial/GUID identification fallback is upstream code.
The controller suppression scan currently assumes Linux `/proc/PID/fd` and
`/proc/PID/comm`. An EmberBSD ownership backend and its runtime checks are
required before accepting this feature. Remote keyboard injection uses the
XDG RemoteDesktop portal; disabling the controller daemon is not a port.

## Inotify regression

Apply the patch to the verified source with zero fuzz. Run the component
regression with the shared EmberBSD GCC16 toolchain:

```sh
python3 probes/plasma-bigscreen/check-inotify.py /absolute/patched-source \
    /absolute/common-gcc16.cmake /absolute/new-regression-work \
    --cmake /absolute/cmake --ninja /absolute/ninja
```

The baseline compiles the real upstream `DeviceWatcher`, then fails to link
its inotify calls. The port links the same source with ECM's provider. The
regression rejects a native toolchain and a non-GCC16 target compiler. It
retains both command sets, logs, compilation databases and a result record.
Cppcheck 2.22.0 and Clang Static Analyzer 23.1.3 report no findings for this
translation unit with the actual target headers and macros. The C++ source
is unchanged. Target execution and process-ownership behavior remain untested.
