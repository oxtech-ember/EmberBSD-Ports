# Native Qt GUI generators without X11

A Linux host prefix can build the Qt GUI libraries needed by generators such as
`qsb` and `qmlcachegen` without selecting a native display server or graphics
provider. In the host pkgsrc configuration select:

```make
PKG_OPTIONS.qt6-qtbase+= software-rendering headless-generators -cups -dbus -gtk3
```

The `headless-generators` option requires native Linux and `software-rendering`.
It disables the Qt XCB, Xlib, Wayland and Qt Wayland scanner features and their
direct buildlinks while
retaining the GUI library and the ordinary Unix support files. It cannot be
combined with the Core-only `host-tools` option. Other host and target Qt
configurations keep their existing defaults.

The option policy can be checked without a build:

```sh
"$HOST_PREFIX/bin/python3.15" pkgsrc/x11/qt6-qtbase/tests/headless-options.py \
    --bmake "$HOST_PREFIX/bin/bmake" --work-parent /absolute/existing/work-directory
"$HOST_PREFIX/bin/python3.15" pkgsrc/x11/qt6-qtbase/tests/software-rendering.py
```

These checks do not establish an installed package or an operational generator.
The target Qt configuration remains separate and may select XCB and EGL/GLES.
