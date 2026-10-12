# Full KWin Wayland package and board sessions

The complete `plasma6-kwin-6.7.5nb1` package cross-builds on macOS with
GCC 16.2, Qt 6.12.0, Frameworks 6.31.0 and Mesa 26.2.4. It carries the
full Wayland compositor: core features, KCM modules, screen locker
integration, global shortcuts and runner plugins. Tests stay enabled in
the build. The optional PipeWire screencast plugin, libeis and the
a11y client remain unported; the PLIST no longer lists the screencast
plugin, and no feature is silently stubbed.

## PLIST repair against the real DESTDIR

The first full packaging run failed the pkgsrc file checks in both
directions. The final PLIST matches the actual install image:

- Removed five stale entries: `include/kwin/utils/drm_format_helper.h`
  (no longer a public header), `include/kwin/wayland/blur.h` and
  `contrast.h` (upstream 6.7 replaced both protocols with
  `ext-background-effect-v1`, whose headers are installed),
  `include/kwin/wayland/textinput_v1.h` (upstream removed the
  text-input-v1 server), and `qt6/plugins/kwin/plugins/screencast.so`
  (requires the unported PipeWire).
- Added 42 real files: the Vulkan renderer headers, `backgroundeffect_v1`
  protocol headers, `SlowKeysPlugin.so`, `kwin_dialog_helper`, its
  desktop file, the `slidingnotifications` effect metadata, additional
  pt_BR docbook output and the locale catalogs produced by this build.

A failed repackage also leaves stale `work.*` caches: `.PLIST_deps`
kept the removed entries and made the permission check fail after the
PLIST was already correct. The cache must be repaired together with the
PLIST, and the recorded `@blddep kf6-kauth-6.31.0` corrected to the
actually installed `6.31.0nb1`.

## Package audit

`packages/NetBSD-aarch64/All/plasma6-kwin-6.7.5nb1.tgz` (14,152,047
bytes) passes the full pkgsrc package checks: file check, script
interpreters, permissions, PIE, RELRO, runtime search paths and
work-directory references. All 1711 payload files match the installed
common sysroot byte for byte (SHA-256 manifest kept in
`kwin-package-audit-r1/package.sha256`).

## Board session

`tests/kwin-session/run-zero3w-headless.sh` runs a bounded private
session on a board without an accepted KMS driver: `kwin_wayland
--virtual --no-lockscreen --no-kactivities --no-global-shortcuts
--exit-with-session=<wrapper>` inside `dbus-run-session`. The wrapper
waits for the compositor socket, runs the Qt Quick client checks
(`tests/qt-quick-gpu/run-zero3w.sh`), records
`org.kde.KWin.supportInformation`, and KWin exits with the wrapper.
The session asserts the compositor socket is removed after exit.

On boards whose Mesa only provides software EGL the session records
`llvmpipe` as the renderer and makes no hardware GPU claim. The
compositor screenshot path (ScreenShot2 over D-Bus with fd passing)
still needs an fd-capable client and is not part of this acceptance.
