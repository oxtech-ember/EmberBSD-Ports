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
