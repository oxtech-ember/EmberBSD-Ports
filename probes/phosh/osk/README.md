# Stevia on-screen keyboard

This probe builds the real [Stevia](https://gitlab.gnome.org/World/Phosh/stevia)
0.58.0 keyboard, formerly named `phosh-osk-stub`. It uses the same GTK3
Wayland and support libraries as the native Phosh profile. Stevia implements
Wayland input-method-v2, virtual-keyboard-v1 and the `sm.puri.OSK0` D-Bus
interface expected by Phosh. This is an experimental native build, not a
pkgsrc package or a secure login session.

## Build and component tests

Copy the whole Phosh probe directory. In the already prepared native
EmberBSD/NetBSD development environment, run as an ordinary user:

```sh
JOBS=2 sh osk/build.sh "$HOME/.cache/phosh-osk" \
  "$HOME/.cache/phosh-support/install" "$HOME/.cache/phoc-native/prefix"
sh osk/test.sh "$HOME/.cache/phosh-osk"
```

The work directory must be new and absolute; its parent must exist.
A fourth build argument can supply the original archive locally.
Paths use letters, digits, `_`, `.`, `/` and `-`. `JOBS` defaults to 2.
The build preserves errors and installs only into `WORK/install`.
The test runner owns a separate Xvfb server and D-Bus session. It does not
use the existing desktop. Logs and environment details remain in
`WORK/logs`. Core dumps are disabled in these helpers.

Dependencies beyond the existing [Phosh support stack](../support.md) are
Hunspell and a dictionary, JSON-GLib, gnome-desktop3, gsettings-desktop-schemas
47 or newer, and the evdev key-code headers from pkgsrc. Tested dictionaries
are read from `/usr/pkg/share/hunspell` and `/usr/pkg/share/myspell`.
`hunspell-en_US` supplies the English dictionary. Russian keyboard layout
support does not itself establish Russian spelling suggestions.

Upstream Meson, GObject generators and `tools/write-layout-info.py` use
Python. The recipe uses the installed Python 3.13 by default; set `PYTHON`
to another absolute interpreter path if required. The private `python3`
alias and Meson interpreter discovery avoid assuming `/usr/bin/python3`.
Project-owned helpers use shell and C.

## Session integration

Add `WORK/install/share` to the session's `XDG_DATA_DIRS`, together with the
support, Phoc and installed pkgsrc data directories. Then start
`WORK/install/bin/phosh-osk-stevia` with Phosh's Wayland display and D-Bus
address. There is no second compositor or replacement keyboard backend.
Use the private profile's settings to enable the screen keyboard:

```sh
gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true
gsettings set mobi.phosh.osk ignore-hw-keyboards true
```

The second setting allows the nested demo to show the OSK even though the
host exposes a physical keyboard. Apply both only inside the isolated
profile, not to the host desktop. The keyboard normally follows focus in
Wayland text fields; its D-Bus name is `sm.puri.OSK0`, object path
`/sm/puri/OSK0`. `SetVisible` and `Visible` implement Phosh's keyboard
control. `--replace` is unnecessary in a fresh D-Bus session.

## Local adaptations

[stevia-portable.patch](stevia-portable.patch) is an AI-assisted local
adaptation. It has not been submitted to or accepted by upstream.

- `logind` becomes an explicit Meson feature, enabled by default. The
  native profile disables it, removes the logind session object and
  disables the Settings action because lock state cannot be established.
  It does not report a fabricated session or unlocked state.
- `dconf_migration` remains enabled by default. The native profile
  disables migration of legacy keyboard settings, suitable for its fresh
  private GSettings profile. That avoids accessing the host's dconf
  database. Existing users' dconf settings are not migrated by this build.
- Linux sealed memfd support is selected only on Linux. NetBSD uses the
  existing POSIX shared-memory path for virtual-keyboard keymaps. Failed
  unlink/truncate operations preserve errors and close their descriptors.
  The regression checks an unaligned 4093-byte shared mapping, lifetime,
  close-on-exec and invalid-size errors.
- The Hunspell dictionary path becomes configurable while retaining the
  upstream default. This permits a private OSK prefix to use the pkgsrc
  dictionaries without copying them.
- The layout generator uses Meson's selected Python interpreter. The
  failed-Wayland-display diagnostic uses portable errno formatting.

No settings application, logind, systemd or secure lock integration is
provided by this probe. The keyboard's installed systemd unit is unused;
the nested launcher supervises the process directly.

## Validation boundary

On 2026-10-06, a fresh native build and private installation completed on
NetBSD 11/aarch64 with the VirtGPU trial kernel, GCC 12.5.0, Meson 1.11.1 and
pkgsrc dependencies. The dynamic dependency audit found the native
`libintl.so.1` and no conflicting `libintl.so.8`.

All 73 Meson test entries passed: schema and AppStream checks, 61 layout
validations, nine upstream component suites and the shared-memory
regression. The Hunspell test used the installed English dictionary.
The fzf and Varnam subcases were explicitly skipped because those optional
completion engines are not installed.
The integrated Phosh session showed the OSK automatically on text focus.
Pointer clicks entered English and Russian text in gedit and saved a file.
The same keyboard appeared in GTK4 Demo's search field. These checks used
Phoc/X11 on a private Xvfb display through a local SSH/VNC viewer.
The GTK3 input-module cache is required; the support builder now creates it. Component tests alone do not prove physical touch input,
composition in every application, lock-screen safety or hardware support.

## Source and license

- Upstream: <https://gitlab.gnome.org/World/Phosh/stevia>
- Original release: <https://sources.phosh.mobi/releases/phosh-osk-stevia/phosh-osk-stevia-0.58.0.tar.xz>
- SHA256: `aba2a67aaabdfc9c0fc4dadd0ef814c593adfaef6d5fe0403c8e332f695e6d9a`
- License: GPL-3.0-or-later; original [license text](LICENSES/GPL-3.0.txt).
  The downloaded source retains authorship and per-file SPDX notices,
  including the Devhelp migration helper and contributed Phosh code.
- The shared-memory regression derives from the adjacent Phosh probe's
  `platform/phosh-portable-build.patch`, with an unaligned-length case.
  The build/test helpers follow the adjacent Phosh and Phoc recipes.
