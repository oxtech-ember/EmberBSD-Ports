# Bigscreen dependency source candidates

These recipes are source candidates. No new dependency package or GCC16 build
is accepted by this source preparation. Qt stays at the common 6.12.0 ABI.
The source pins and their verification limits are in `dependency-sources.json`.

## Qt WebEngine

The recipe imports all 1,180 portability patches from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`, including its NetBSD backend.
WebEngine 6.11.2 is the verified stable source release in the official 6.11
index. Qt has announced separate WebEngine versioning beginning with 6.140;
the inspected development index contains 6.140.0-rc. Recheck the official
stable index before building. An RC is not selected as a stable release.

`WEBENGINE_VERSION` selects the source archive and package version.
`QTVERSION` selects the common Qt ABI. The upstream project derives its module
version from the selected Qt BuildInternals. The PLIST uses `QTMODULE_VERSION`
for those paths. This requires confirmation by an actual configure and package.
The archive has not been fetched in this continuation. Its BLAKE2s, SHA512 and
size come from the pinned pkgsrc distinfo, not from a new archive check.

The candidate retains fatal linker warnings. The Linux glibc requirement
remains active; NetBSD does not require glibc. The recipe selects common
FFmpeg 9 and removes the inherited forced Vulkan disable. Existing backend,
PDF, codec, audio and system-library settings otherwise remain visible.
These settings require real source configuration and compilation.

Apply `patches/patch-toolkit-qt-webengine-selection` with zero fuzz only to a
fresh prepared toolkit export, then overlay the complete recipe directory.
The normal toolkit exporter does not yet select this candidate. Updating its
registry and selection regression is a separate integration step.
No accepted Qt provider must be replaced before package and consumer checks.

## BluezQt

The 6.31.0 archive is SHA256-verified. Four source patches select NetBSD byte
order, keep the Linux worker implementation and declaration inside the same
platform guard, and describe NetBSD as a D-Bus client platform. The recipe
keeps ECM platform validation enabled. It does not set an ignore-platform
escape. QML support and all upstream tests stay enabled. The PLIST is derived
from the exact source install declarations and remains a package candidate.

The source also selects macOS byte-order definitions for native memory checks.
The explicit `macOS` metadata entry uses ECM's actual platform identifier.
Native configuration passes with Qt 6.12.0, ECM 6.31.0, testing enabled and the
platform check enabled. The subsequent build was interrupted. No native test
invocation completed, and no complete native library or memory pass is accepted.
`check-bluezqt-native.py` provides the full source, QML and upstream-test runner
for a later permitted work directory. Only its Python syntax is checked here.

This client adaptation is not a native Bluetooth implementation. Upstream's
non-Linux rfkill state remains `Unknown`. NetBSD HCI `BTF_UP` and `BTF_RUNNING`
are adapter states, not hardware and software radio-block states. They must
not be relabelled as Linux rfkill states. The available HCI ioctl interface
also does not supply the BlueZ 5 ObjectManager, Adapter1, AgentManager1,
ProfileManager1, GATT and OBEX D-Bus services expected by the client.
The native service and radio-switch contract remain required work.

## KDE Connect

The official release-service index lists 26.08.2. Its archive and checksum are
not yet verified, so this candidate does not provide a speculative recipe.
Bigscreen requires the real `org.kde.kdeconnect` QML module and daemon.
A configure placeholder or an empty QML module cannot satisfy that contract.

## Source checks and build gates

Run `check-dependency-sources.py` with the pinned pkgsrc directory and verified
BluezQt archive. The check verifies source checksums, exact patch contexts,
unchanged Linux rfkill and codec source, the active Linux glibc requirement,
NetBSD/GNU GN selection, inherited WebEngine patches and recipe boundaries. It does not
compile source and is not a substitute for Cppcheck, Clang Static Analyzer,
ordinary GCC16 package checks or target execution. These checks remain pending
for the new candidates. The earlier accepted DeviceWatcher probe has its own
separate result and does not establish these dependencies.
