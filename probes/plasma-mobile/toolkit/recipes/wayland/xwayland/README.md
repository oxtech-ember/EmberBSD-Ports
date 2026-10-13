# Xwayland for the complete Plasma session

This recipe updates pkgsrc `wayland/xwayland` to stable Xwayland 24.1.14.
The [upstream release announcement](https://lists.x.org/archives/xorg-announce/2026-October/003749.html)
provides the archive SHA256. The release date is 2026-10-07.
The recipe derives from pkgsrc revision
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
EmberBSD recipe changes are AI-assisted. Upstream authorship and licenses remain.

Plasma Workspace 6.7.5 starts `kwin_wayland_wrapper --xwayland` in its
classic session. Its `ksmserver` process selects the Qt `xcb` platform.
The full session therefore needs Xwayland even when KWin uses Wayland.
A direct KWin virtual-output probe has a different acceptance boundary.

The recipe uses the common Mesa, libdrm, Wayland, and libei providers.
Glamor, GLX, DRI3, and the upstream Xvfb test target stay enabled.
The XKB data and compiler paths refer to the installed target prefix.
Cross builds use the common native Wayland scanner and its hash receipt.
The inherited pkgsrc `secure-rpc=false` setting retains the platform's
existing AUTH_DES boundary. It does not disable local X11 authentication.

Upstream `test/meson.build` remains active. Cross compilation must not run
AArch64 test executables on the build host. Preserve the build directory
for target unit tests and Xwayland/Xvfb integration tests. Piglit and
rendercheck are optional upstream integration harnesses.

The `nb1` patches correct signedness in seat and tablet identifiers and the
shared source-line diagnostic. They preserve message text and protocol behavior.
[Actual-source formatting checks](tests/README.md) cover integer boundaries,
strict target compiler diagnostics and native ASan/UBSan execution.
The [source-analysis scope](tests/source-analysis.md) records the remaining
analyzer limitations separately from the corrected errors.

Archive hashes and Meson option names are verified against this release.
Package compilation, source analysis, target tests, and an installed Plasma
login remain separate gates. No board runtime result is claimed here.
