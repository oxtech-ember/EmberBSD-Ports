# Xwayland for the complete Plasma session

This recipe updates pkgsrc `wayland/xwayland` to stable Xwayland 24.1.14.
The [upstream release announcement](https://lists.x.org/archives/xorg-announce/2026-October/003749.html)
provides the archive SHA256. The release date is 2026-10-07.
The recipe derives from pkgsrc revision
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
EmberBSD recipe changes are AI-assisted. Upstream authorship and licenses remain.

Plasma Workspace 6.8.0 starts `kwin_wayland_wrapper --xwayland` in its
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

## Software rendering and driver path

The `nb4` revision corrects two defects found on a machine without hardware
DRM, where Xwayland falls back to software rendering through `wl_shm`
(`Failed to initialize glamor, falling back to sw`).

`patch-hw_xwayland_xwayland-shm.c`: `os_create_anonymous_file()` creates a
memfd, seals it and calls `posix_fallocate()`. On NetBSD and EmberBSD that
call returns `EINVAL` for a memfd, because the kernel handles it for vnodes
only. The function treated every non-zero result as "no space", closed the
descriptor and returned -1: no `wl_shm` pool, and X11 windows without content.
`EINVAL`, `EOPNOTSUPP` and `ENOSYS` now select the `ftruncate()` path that the
code already used without `posix_fallocate()`. On EmberBSD, FFS and tmpfs
return `EOPNOTSUPP` as well. The file is always sized with `ftruncate()`
afterwards, because the NetBSD manual page says that `posix_fallocate()` does
not change the file size. Other errors, including `ENOSPC`, `EFBIG` and `EIO`,
are still returned. This is a workaround in the application. The cause is in
the OS: `posix_fallocate()` on a memfd should work or return `EOPNOTSUPP`.

`patch-include_meson.build`: `DRI_DRIVER_PATH` came from `dridriverdir` in
`dri.pc`. A cross build runs pkg-config with `PKG_CONFIG_SYSROOT_DIR`, which
prepends the build sysroot to the value. The binary then searched the build
machine path for the software renderer (`GLX: could not load software
renderer`) and X11 clients had no GLX extension. The path now derives from the
installed prefix and libdir, `/usr/pkg/lib/dri`, like the XKB paths above.
The other pkg-config variables the build reads are `xkbconfigdir` and `bindir`
(replaced by the `-Dxkb_*` options), `fontrootdir` (`fontutil` is not
installed, so the prefix default applies), and the `wayland-scanner` and
`wayland-protocols` paths, which only name build inputs.

[`tests/shm-fallocate.rb`](tests/README.md) runs the real function from the
upstream and patched sources with controlled `posix_fallocate()` results.
It also builds the same function for the target, where the unmodified libc call
shows the `memfd` behavior. [`tests/xwayland-binary.rb`](tests/README.md) checks
a built `bin/Xwayland` for build machine paths and for
`DRI_DRIVER_PATH=/usr/pkg/lib/dri`. Hardware DRM, glamor and the accelerated
path are not covered by these changes or tests.

## Shared socket directories

The `nb3` recipe supplies the `x11_runtime` rc.d service on EmberBSD.
It runs after `cleartmp` and before normal login services. It creates
`/tmp/.X11-unix` and `/tmp/.ICE-unix` as root:wheel with mode 1777.
KWin's unprivileged Xwayland launcher requires the first directory.
The service never removes sockets or changes an existing directory's owner.
It rejects symlinks, wrong ownership, wrong permissions and a per-user `/tmp`.
The full-session preflight checks the same parent and both socket directories.
A valid child is not sufficient when another user can replace it through an unsafe parent.
The checks use BSD `stat -f '%u:%g:%p'` and require `0:0:41777`.
The full mode includes the directory type and sticky bit; `%Lp` omits the sticky bit.
Resolve an unsafe existing path separately before starting a desktop.

pkgsrc installs the example into `share/examples/rc.d/x11_runtime`.
By default, it does not copy rc.d scripts into `/etc/rc.d` or start them.
For a native installation, root can select normal pkgsrc script management:

```sh
PKG_RCD_SCRIPTS=yes pkg_add -U /absolute/xwayland-24.1.14nb4.tgz
/etc/rc.d/x11_runtime start
```

Keep the installed service in `/etc/rc.d`. No enable flag is required.
It runs again after the next boot clears `/tmp`.
For an already installed package, review and install its matching example:

```sh
install -o root -g wheel -m 0755 \
    /usr/pkg/share/examples/rc.d/x11_runtime /etc/rc.d/x11_runtime
/etc/rc.d/x11_runtime start
```

Do not overwrite a locally modified service without reviewing its changes.
With `PKG_RCD_SCRIPTS=yes`, pkgsrc deinstallation removes an unmodified
managed service. It does not remove live socket directories. Package installation does not start a
session or start this service automatically.

Run `ruby tests/runtime-service.rb` from this recipe for the service and
full-session preflight regressions. Host tests use real BSD `stat` formatting,
controlled ownership and command failures. They reject the previous `%Lp` check. They do not claim a target boot or a Plasma login.

Run `ruby tests/package-lifecycle.rb /absolute/xwayland-24.1.14nb4.tgz /absolute/new-results`
to test the actual generated package helper. It checks the disabled default,
explicit script management, repeat installation and modified-file preservation.
Only its configuration data path is redirected into a private test prefix.
