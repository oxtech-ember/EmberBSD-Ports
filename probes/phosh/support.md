# GTK and service-client support libraries

**2026-10-06: all four support builds completed in a fresh private prefix
on NetBSD 11/aarch64. The GTK3 demo was visibly rendered over Wayland by
nested Phoc. This establishes a toolkit/client-library build and a GTK
display check, not hardware support or a complete Phosh session.**

## Reproduce

Run the [support builder](build-support.sh) as an ordinary user:

```sh
sh build-support.sh /absolute/path/to/new-work-directory
```

The directory must not exist. Its parent must exist, and its path must
contain only letters, digits, `_`, `.`, `/` and `-`. The result is installed
in `NEW_WORK_DIRECTORY/install`; existing pkgsrc packages are not replaced.
The helper defaults to two parallel compiler jobs. Set `JOBS=1` for a
smaller machine.

For offline use, append a directory containing all four archives listed
in [support-sources.tsv](support-sources.tsv). Online and offline runs
both verify each pinned SHA256 before extraction. Meson's automatic
subproject downloads are disabled. Failed stages retain their nonzero
exit status and print the location of their complete logs.

The native development environment needs a C compiler, Meson, Ninja,
pkgconf, curl, tar, patch, NetBSD `sha256`, GLib development tools,
GTK's existing dependencies, and Wayland client/protocol development
packages. The probe uses the already installed pkgsrc GNOME environment;
it does not install missing packages itself.

The helper is POSIX shell. Upstream Meson and GLib code generators use
Python. `PYTHON` defaults to `/usr/pkg/bin/python3.13` and must be an
absolute executable path. The helper creates only a private `python3`
symlink under the work directory.

To use the resulting development libraries, set `work` to that directory:

```sh
export PKG_CONFIG_PATH="$work/install/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$work/install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

GObject introspection generation is disabled for GTK, GNOME Bluetooth and
libfeedback in this build profile. The separate
[ModemManager client builder](client-libs/README.md) supplies libmm-glib;
it is not one of these four support builds.

The support builder explicitly generates GTK3's `immodules.cache`. GTK's
Meson post-install updates GIO caches but does not create this GTK3 cache.
Without it, text fields fall back to the simple input context and do not
activate the Wayland keyboard. For an older private prefix, run
`sh gtk3/update-im-cache.sh PREFIX`; the nested-session regression checks
the missing-cache fallback and the real Wayland context.

## Components and evidence

The fresh helper run used NetBSD 11/aarch64 with the EmberBSD `EMBER64`
kernel from OS revision `b4f718d`, GCC 12.5.0, Meson 1.11.1 and GLib 2.88.1.
All four installed versions were checked through their pkg-config files.

| Component | Build profile | Verified result |
|---|---|---|
| GTK 3.24.52 | X11 and Wayland enabled; demos enabled; tests disabled; unchanged pkgsrc patches | Libraries and demo installed; GTK demo visibly rendered through nested Phoc's Wayland socket |
| GNOME Bluetooth 46.2 | Unmodified upstream source; `sendto` disabled | Library installed; device and device-utils tests passed; integration test skipped with status 77 |
| feedbackd 0.7.0 / libfeedback | Daemon and udev integration disabled; client tests enabled | Library installed; schema validation and `lfb-event` passed |
| callaudiod 0.1.99 / libcallaudio | Daemon disabled by the local build option | Library and `callaudiocli` installed; no test suite run by this helper |

The two successful feedback tests are one schema check and one client
event test. They do not test the feedback daemon. GNOME Bluetooth's
skipped integration test is not counted as a pass. GTK's complete test
suite was not run; its recorded runtime evidence is the visible demo.

The resulting libraries retain their real D-Bus implementations.
The private installation contains no feedbackd/callaudiod daemon or
D-Bus activation service file. Bluetooth operations still need a
compatible BlueZ service. Haptic/audio/LED feedback and call audio routing
still need their real services and device integration. None of those
hardware operations is established by this support build.

Upstream callaudiod 0.1.99 declares itself deprecated in its README.
This probe uses its existing client API required by Phosh.

## Native gettext ABI

The installed NetBSD GLib/GIO stack uses `/usr/lib/libintl.so.1`.
Direct Meson builds would also select pkgsrc's `libintl.so.8`,
creating a mixed gettext dependency set. The private
[pkg-config wrapper](native-pkg-config.sh) replaces the `-lintl` token with
the explicit native library path. Its substitution uses POSIX extended
regular expressions supported by NetBSD `sed`.

Fresh builds use this wrapper from the first Meson setup.
The helper's GTK `ldd` regression check rejects `libintl.so.8`.
Inspection of the installed GTK, GNOME Bluetooth, libfeedback and
libcallaudio libraries confirmed native `libintl.so.1`, without
`libintl.so.8`. No installed `.pc` file or system library was modified.

This check addresses the observed gettext conflict. It does not claim
that every library dependency or every GTK feature has been validated.

## Sources and local changes

[support-sources.tsv](support-sources.tsv) is the executable source
manifest: archive filename, SHA256 and original URL. The official sources
downloaded on 2026-10-06 are:

| Component | Original archive |
|---|---|
| GTK 3.24.52 | [GNOME release archive](https://download.gnome.org/sources/gtk/3.24/gtk-3.24.52.tar.xz) |
| GNOME Bluetooth 46.2 | [GNOME release archive](https://download.gnome.org/sources/gnome-bluetooth/46/gnome-bluetooth-46.2.tar.xz) |
| feedbackd 0.7.0 | [Phosh release archive](https://sources.phosh.mobi/releases/feedbackd/feedbackd-0.7.0.tar.xz) |
| callaudiod 0.1.99 | [Original Mobian GitLab tag archive](https://gitlab.com/mobian1/callaudiod/-/archive/0.1.99/callaudiod-0.1.99.tar.gz) |

The build checks the pinned bytes; this is not a claim that every archive
was independently authenticated by an upstream signature.
Downloaded archives, extracted sources, binaries and complete logs remain
outside Git. Upstream copyright and license notices remain intact.

- The ten [GTK pkgsrc patches](gtk3/README.md) are unchanged third-party
  patches, not new EmberBSD adaptations. Their exact SHA256, Git blob ID
  and original URL are recorded separately. This includes the original
  note that the `gtklabel` patch was rejected by GTK upstream.
- [feedback/client-tests.patch](feedback/client-tests.patch) limits the
  umockdev dependency and test wrapper to daemon-enabled builds. The
  library test implementation and public API are unchanged.
- [callaudio/client-only.patch](callaudio/client-only.patch) introduces a
  default-enabled daemon option and omits the daemon target and its
  D-Bus activation file when disabled. The real client library and CLI
  remain built; library implementation and public API are unchanged.

The feedback and callaudio patches and the shell integration are local,
AI-assisted work. The local patches have not been submitted to or
accepted by their upstream projects. They do not inherit an upstream
acceptance claim from the separate pkgsrc GTK patches.

GTK source files retain their LGPL-2.0-or-later notices; GNOME Bluetooth
client sources retain LGPL-2.1-or-later notices. Libfeedback and
libcallaudio client sources likewise declare LGPL-2.1-or-later.
The original feedbackd [COPYING](feedback/LICENSES/COPYING) and
[COPYING.LIB](feedback/LICENSES/COPYING.LIB), and callaudiod
[COPYING](callaudio/LICENSES/COPYING), are copied verbatim from the pinned
archives. Their [copy provenance](feedback/LICENSES/README.md) and
[callaudiod license notes](callaudio/LICENSES/README.md) preserve the
distinction between library notices and archive-wide metadata.
