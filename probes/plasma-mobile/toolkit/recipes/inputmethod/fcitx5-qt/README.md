# Fcitx Qt6 adapter

This recipe builds Fcitx5 Qt 5.1.16 with the common Qt 6.12 provider.
Qt4 and Qt5 are disabled. The Qt6 Wayland integration remains enabled.
The [Fcitx source record](../fcitx5/README.md) owns release hashes and package boundaries.

CMake loads compiler settings from the resolved `Fcitx5Utils_DIR`.
The target installation path does not identify a readable build-host directory.
The recipe also passes pkgsrc-selected native `msgfmt` and `msgmerge` to FindGettext.
Target Fcitx and gettext libraries remain normal dependencies.
The existing plugin path patch preserves the target Qt6 plugin directory.

The metadata check confirms native and cross tool paths and executes both native tools.
The new compiler-settings patch applies with zero fuzz to the recorded release.
Complete cross packaging and target Qt input acceptance remain pending.
The CMake and recipe adaptations are AI-assisted EmberBSD work, not accepted upstream.
