# Qt platform-theme initialization contract

The Qt 6.12.0 KDE theme constructor calls `refresh()`. That function emits a
QPA theme notification before `createPlatformTheme()` returns and assigns
`QGuiApplicationPrivate::platform_theme`. A QPA that enables synchronous event
delivery can therefore enter `processThemeChanged()` with no installed theme.
`handleThemeChanged()` then passes null to `QStyleHintsPrivate::update()`.
The KDE factory takes this path only when `KDE_SESSION_VERSION` is at least 4.
The modern KDE path uses a value greater than 4. A test that does not admit the
KDE theme does not reproduce this initialization sequence.

The recipe patch suppresses the entire notification before theme installation.
The existing application initialization then reads the installed theme's style
hints, palette, fonts and theme hints. Notifications after installation retain
the original cache updates, font policy and application-event delivery.

Run the focused contract with a read-only Qt 6.12.0 source tree and a new output
directory:

```sh
ruby check.rb /absolute/qtbase-everywhere-src-6.12.0 /absolute/new-evidence
CXXFLAGS='-g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  ruby check.rb /absolute/qtbase-everywhere-src-6.12.0 /absolute/new-asan-evidence
```

The runner copies only `qguiapplication.cpp` before applying the recipe patch.
It compiles actual notification, style-update and KDE-constructor bodies.
The modern KDE factory prefix, theme assignment and post-assignment state
initialization statements are also extracted and checked against the source.
Synchronous QPA delivery, configuration reads and Qt object services are
controlled. The legacy KDE 4 factory path is outside this contract.

The upstream constructor path must fail at the named null-theme check.
The patched path covers repeated constructor notifications, refused KDE
versions, generic-theme initialization, late changes, an explicit application
font and an absent application. Compiled mutations must reach their exact
named assertions. Signals, deadlines and sanitizer diagnostics are failures.
The process checks also exercise a descendant that retains an output pipe.
These are host source-contract checks. They do not execute a complete Qt
library, KWin, a compositor session or target hardware. Package lifecycle and
installed standard-session acceptance remain separate checks.
