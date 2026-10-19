# LXQt session policy

The default meta-package option is `wayland`. It selects LXQt's Wayland
session, the common labwc 0.20.2 compositor, swaylock 1.8.6, swayidle 1.9.0 and
the common Qt 6.12 Wayland runtime. These are current stable releases.
[LXQt's configuration guide](https://lxqt-project.org/blog/2026/05/01/how-to-enable-wayland-lubuntu-26-04/)
uses labwc and swaylock together. The compositor retains the panel, file
manager and LXQt Session Settings interfaces.

The revision-6 session defaults set `compositor=labwc` and
`lock_command_wayland=swaylock`. The meta-package requires this revision.
`lxqt-leave --lockscreen` calls `LXQt::ScreenSaver::lockScreen`. On Wayland,
that object reads `lock_command_wayland` from the session settings and starts
the command through `QProcess`. User settings retain their existing priority.
The default-data patch does not replace other session settings.

The explicit X11 option selects i3lock 2.16 and xss-lock 0.3.0. Its lock command
is `i3lock --nofork`; its X11-only autostart command is
`xss-lock -- i3lock --nofork`. The existing configuration filename is retained.
No meta option depends on XScreenSaver or xlockmore. Their pinned recipes
require GTK3 and GTK2, respectively. The X11 alternative remains unqualified;
its authentication and idle behavior have not been accepted on the target.

`check-meta-dependencies.py` queries ordinary pkgsrc metadata for the default
Wayland selection and explicit X11 selection. It checks that each has its
required compositor or window manager, locker and idle consumer. It rejects
the X11 graph as a Wayland result. Neither direct graph may contain GTK2,
GTK3, XScreenSaver or xlockmore.

`check-session-defaults.py` verifies the pinned original source and applies
the actual data patch at fuzz zero. It checks the lock route in the actual
session and liblxqt source. The old and two incomplete defaults are rejected.
This is a source/data check. It does not execute a locker or authentication.

Complete package and runtime acceptance remain pending. Required work includes
the Wayland wrapper's declared shell and qdbus runtime provider, panel plugins,
input configuration, the remaining meta-package applications, normal package
lifecycle and an installed graphical session. Compositor rendering, input,
screen locking, idle policy and resume need independent target checks.
