# LXQt session policy

The default meta-package option is `wayland`. It selects LXQt's Wayland
session, the common labwc 0.20.2 compositor, swaylock 1.8.6, swayidle 1.9.0 and
the common Qt 6.12 Wayland runtime. These are current stable releases.
[LXQt's configuration guide](https://lxqt-project.org/blog/2026/05/01/how-to-enable-wayland-lubuntu-26-04/)
uses labwc and swaylock together. The compositor retains the panel, file
manager and LXQt Session Settings interfaces.

The session defaults set `compositor=labwc` and
`lock_command_wayland=swaylock`. The meta-package requires revision 6 or later.
`lxqt-leave --lockscreen` calls `LXQt::ScreenSaver::lockScreen`. On Wayland,
that object reads `lock_command_wayland` from the session settings and starts
the command through `QProcess`. User settings retain their existing priority.
The default-data patch does not replace other session settings.

The explicit X11 option selects i3lock 2.16 and xss-lock 0.3.0. Its lock command
is `i3lock --nofork`; its X11-only autostart command is
`xss-lock -- i3lock --nofork`. The existing configuration filename is retained.
Its displayed name is `X11 Screen Lock`. Old XScreenSaver translations are
not merged into this replacement entry. Reviewed translations remain pending.
No meta option depends on XScreenSaver or xlockmore. Their pinned recipes
require GTK3 and GTK2, respectively. The X11 alternative remains unqualified;
its authentication and idle behavior have not been accepted on the target.
The old `xfce4-wm` alternative is unsupported because its UI dependency needs
GTK3. The normal pkgsrc option guard rejects an explicit request for it.

`check-meta-dependencies.py` queries ordinary pkgsrc metadata for the default
Wayland selection and explicit X11 selection. It checks that each has its
required compositor or window manager, locker and idle consumer. It rejects
the X11 graph as a Wayland result. Neither direct graph may contain GTK2,
GTK3, XScreenSaver or xlockmore.
The fourth check requires a package refusal for `-wayland xfce4-wm`.

The recursive default Wayland graph resolves 176 registered providers and
32 source-recipe nodes without GTK2, GTK3, Qt4 or Qt5. Missing providers are
queried through ordinary pkgsrc `DEPENDS`; this graph is not a completed
package build or an installed runtime closure. It includes the source recipe
for PCManFM-Qt, whose package was installed after that node was queried.

`check-session-defaults.py` verifies the pinned original source and applies
the actual data patch at fuzz zero. It checks the lock route in the actual
session and liblxqt source. The old and two incomplete defaults are rejected.
This is a source/data check. It does not execute a locker or authentication.
The X11 label and command are checked from the patched desktop input.

The ordinary GCC16 revision-7 package completes all 200 build steps and the
normal pkgsrc package checks. Its SHA256 is
`8adff3ace0442e50c455deac0d4b5091979df55018bf731a7546c4eecab2e5b6`.
The actual archive contains the three selected commands in
`share/lxqt/session.conf`. Its X11 autostart entry has the new name and no
old localized names. All 174 payload paths match the existing package
manifest. All 50 C++ and header inputs are unchanged. This package is not
installed; the common sysroot still has the accepted revision-5 session.

Complete closure and runtime acceptance remain pending. Required work includes
the Wayland wrapper's declared shell and qdbus runtime provider, panel plugins,
input configuration, the remaining meta-package applications, normal package
lifecycle and an installed graphical session. Compositor rendering, input,
screen locking, idle policy and resume need independent target checks.
