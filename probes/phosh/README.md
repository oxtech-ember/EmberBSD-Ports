# Native Phosh on EmberBSD

**2026-10-06: Phosh 0.58.0 builds and starts natively on NetBSD 11/aarch64
inside the existing GNOME/X11 desktop.** The nested Phoc compositor uses
its X11 backend and pixman software rendering. The home screen, application
list and keyboard search are visible. Launching gedit from Phosh, typing
and saving text through its Wayland window were verified.
GTK3 Demo was launched as a second application; the overview displayed
both thumbnails and selecting the editor returned it to the foreground.
The extended profile adds Stevia 0.58.0 and GTK 4.22.4. Screen-keyboard
clicks entered English and Russian text in gedit and saved the document.
GTK4 Demo was launched from Phosh and displayed its search keyboard.

This is an experimental nested session. It does not establish a working
phone image, direct display/input drivers, GPU acceleration, modem,
Wi-Fi controls, suspend, screen locking or physical touchscreen support.
Missing platform services are reported or their controls are excluded.
No success-returning replacement libraries are used.

## Build

Copy this entire directory to an EmberBSD/NetBSD 11 development machine.
Use an ordinary user and the installed pkgsrc GNOME environment from the
[GNOME example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/desktop/gnome-utm).
Each work directory must be new, absolute and have an existing parent.
Paths must contain only letters, digits, `_`, `.`, `/` and `-`.

```sh
sh build-support.sh "$HOME/.cache/phosh-support"
sh phoc/build.sh "$HOME/.cache/phoc-native"
sh phoc/test.sh "$HOME/.cache/phoc-native"
sh osk/build.sh "$HOME/.cache/phosh-osk" \
  "$HOME/.cache/phosh-support/install" "$HOME/.cache/phoc-native/prefix"
sh gtk4/build.sh "$HOME/.cache/phosh-gtk4"
sh build-shell.sh "$HOME/.cache/phosh-shell" \
  "$HOME/.cache/phosh-support/install" "$HOME/.cache/phoc-native/prefix"
```

The optional [Stevia keyboard](osk/README.md) needs Hunspell and JSON-GLib.
The [GTK4 recipe](gtk4/README.md) fixes NetBSD memfd mapping and installs
only in its private prefix. Existing support builds need their GTK3 input
cache once: `sh gtk3/update-im-cache.sh /absolute/support/install`.
New support builds perform this step automatically.

See [support libraries](support.md) and [Phoc](phoc/README.md) for their
required development dependencies. The shell additionally needs
AppStream, evolution-data-server, fribidi, gcr, gnome-desktop3,
gsettings-desktop-schemas, gudev, libhandy, polkit, libsoup3, libsecret,
libupower, PAM, PulseAudio development files and `xsltproc`.
The helpers stop with the real error when a dependency is missing.
They do not install or replace system packages.

All source archives come from pinned original URLs and are SHA256 checked.
Optional final arguments accept local archives: a directory for the first
two builders, the Phosh archive file for `build-shell.sh`. Meson automatic
downloads are disabled. `JOBS` defaults to 2. Upstream Meson and code
generators use Python; our helpers use shell/C and create only a private
`python3` alias. Complete logs remain under each build directory.

The support prefix contains GTK 3.24.52 with Wayland, GNOME Bluetooth
46.2, libfeedback 0.7.0 and libcallaudio 0.1.99. Phoc 0.58.0 uses its
bundled wlroots 0.20.2 and gmobile 0.7.4. The
[native pkg-config wrapper](native-pkg-config.sh) selects the installed
GLib stack's native `libintl.so.1` and avoids mixing gettext ABIs.

## Run

From a terminal in the existing X11 desktop, with its normal `DISPLAY`
and X authority, run:

```sh
sh run-nested.sh "$HOME/.cache/phosh-shell" \
  "$HOME/.cache/phosh-osk/install" "$HOME/.cache/phosh-gtk4/install"
```

The launcher reads the support/Phoc prefixes recorded by the shell build.
The optional second and third arguments select Stevia and private GTK4.
Without them, the earlier GTK3-only profile remains available.
It creates a fresh private session directory, settings backend and D-Bus
session. Only Phoc sees the host X11 display; Phosh and D-Bus-activated
applications receive the nested Wayland display. GTK4 clients select the
Cairo renderer; both toolkits use their Wayland input method. Stevia offers
English and Russian layouts, including automatic display on text focus.
The requested output is 360x540; GNOME on the tested
800x600 desktop constrained its usable height to 531 pixels.

Phosh starts unlocked for this visual experiment. Idle locking is disabled
only in the private settings. A solid background avoids missing host
wallpaper files. This is not a secure login session.

- `Ctrl+Shift+F9`: toggle the overview.
- `Ctrl+Shift+F10`: open the application list.
- Choose **Show All Apps** to include desktop applications. Use Tab,
  Shift+Tab and Enter, or ordinary pointer input where available.
- Press Ctrl-C in the launching terminal to end the nested session.
  Closing only its X11 window may leave the processes running.

The launcher does not alter `.xsession`, XDM or the active GNOME settings.
It keeps session files for inspection; their path is printed and recorded
in `last-session.txt`. A path exceeding NetBSD's Unix-socket limit is
rejected before launch. The supervisor reports an OSK failure and bounds
child cleanup even if a keyboard process is stopped. Xwayland is disabled; X11-only applications cannot
run inside this profile.

## Verified boundaries

Fresh builds and runtime checks used EmberBSD `EMBER64` from OS revision
`b4f718d`, NetBSD 11/aarch64, GCC 12.5.0, Meson 1.11.1 and pkgsrc
`11.0_2026Q2` dependencies on 2026-10-06.

| Check | Result |
|---|---|
| Support helper, compositor helper, shell helper | Fresh native builds completed in private prefixes |
| GNOME Bluetooth | 2 tests passed; integration test skipped |
| libfeedback | Schema validation and event test passed |
| gmobile | 7 suites passed |
| Phoc | 19 protocol/compositor tests passed using isolated Xvfb |
| Phosh local regressions | HKS 1, keybindings 3, backlight 2 and shared memory 2 passed; network UI/resource validation passed |
| Phosh desktop | Home screen, app list, keyboard search, gedit launch and text save verified |
| Repeated launch | Own shell terminated and relaunched; host GNOME remained running |
| Stevia | Native build; all 73 test entries passed, with optional fzf/Varnam subcases skipped |
| GTK4 | Native build; 12 shared-memory cases, rendered frames, Demo and Widget Factory passed |
| Input cache | Missing-cache fallback reproduced; installed GTK3 selects the real Wayland module |
| Extended session | Screen clicks, English/Russian OSK text saved in gedit; GTK4 Demo and its keyboard displayed |
| Process lifetime | Normal exit, OSK crash and stopped OSK cleanup passed; helper signal cancellation passed |

The complete upstream Phosh test suite was not run. GTK's full test suite
and physical-device functionality remain unverified. Mouse automation in
the UTM client did not reliably move the guest pointer; recorded input
checks also ran on a separate Xvfb display through a localhost-only SSH/VNC viewer. This proved
pointer navigation and OSK clicks through X11, not UTM USB or touch input.
The extended checks used the experimental EMBERGPU kernel; no GPU result
is inferred from these software-rendered sessions.

Run `sh test-nested.sh SHELL_WORK OSK_PREFIX [GTK4_PREFIX]` for the real
isolated session and GTK3 input-cache regression. Repeat with
`PHOSH_TEST_TERMINATION=osk` or `stopped-osk` for failure cleanup.
The OSK and GTK4 directories also provide component/runtime and cancellation
checks. These tests own their displays; they do not use the visible desktop.

[Platform patches](platform/README.md) omit Linux logind and rfkill.
[Network profile](platform/networkmanager.md) omits NetworkManager-dependent
Wi-Fi/VPN/WWAN controls, including the dependent ModemManager path.
Applications can use the host OS's existing network. Brightness, torch,
suspend and hardware kill-switch monitoring are unavailable. Service
warnings remain for session management, Polkit/ConsoleKit, sensors and
calls. PulseAudio's GVC emits port assertions; audio behavior is unverified.
The red battery indicator does not establish actual battery integration.

The installed system GTK4 still has the memfd issue. Selecting Cairo alone
does not fix it; the third launcher argument supplies the patched library.
GTK4 Vulkan and GStreamer media are disabled in this build. The private
profile includes **GTK3 Demo**; **GTK Demo** uses the selected GTK4 prefix.
Desktop GTK dialogs can exceed the narrow output; mobile adaptation of
every desktop application is outside this port.

The independent [client-library probe](client-libs/README.md) built genuine
libmm-glib 1.24.2 with two passing tests. libnm 1.54.3 did not compile.
Neither library is required by the disabled-network nested profile.

## Provenance

[Phosh 0.58.0](https://sources.phosh.mobi/releases/phosh/phosh-0.58.0.tar.xz)
SHA256: `b936af34ebed15b29d4f941c48aa328a47da9c2e51cbf6ef89040a90f522ed73`.
The build applies the four patches documented under [platform](platform/):
optional platform integrations, optional NetworkManager, portable C/build
fixes and optional keybindings for older GNOME Shell schemas.
Sources remain separate from this recipe repository.

Local adaptations and helpers are AI-assisted and have not been submitted
to or accepted by upstream. Original licenses and attribution are retained.
See the component documentation for original URLs, hashes, copied pkgsrc
patch identifiers and license texts.

The original `probe.sh` and `gmobile-device-tree-test.patch` are retained as
the earlier unmodified-Phosh dependency experiment. That probe still stops
at missing GTK3 Wayland and is not the working session recipe above. It was
moved unchanged from Examples commit `d501139` in Ports commit `809eff7`.
