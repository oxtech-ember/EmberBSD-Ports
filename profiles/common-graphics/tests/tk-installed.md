# Installed Tk 9.1 X11 contract

[tk-installed.tcl](tk-installed.tcl) exercises the installed Tcl/Tk APIs.
Run it in a fresh `tclsh9.1` process with an X11 display. Use the ordinary
GCC16 package and its complete runtime dependency closure.

```sh
DISPLAY=:99 /usr/pkg/bin/tclsh9.1 \
    /absolute/EmberBSD-Ports/profiles/common-graphics/tests/tk-installed.tcl \
    /absolute/new/tk-output /usr/pkg/lib/libtcl9tk9.1.so
```

The output directory must not exist. The selected shared library must exist.
The script mounts the ZipFS appended to that library. It initializes Tk from
the embedded `tk_library/tk.tcl`, then checks the actual loaded library path.
It retains the installed external script tree.

The contract checks Unicode text, character indices, tags, font metrics,
themed button state, PNG file and memory round trips, RGB and alpha values,
canvas coordinates, mapped X11 window identifiers, queued virtual events,
idle callbacks and window destruction. It retains `pixels.png` for inspection.
Background callback errors fail the process. Waits have five-second deadlines.
A fifteen-second event-loop timer also fails the process. A supervising runner
must bound the whole process, including a stalled X11 connection or library load.
Exit zero and a `PASS` line are both required.

These checks do not compare screen pixels or prove font glyph coverage.
They do not exercise CUPS jobs, an AT-SPI service, physical input, a window
manager, an accelerated display, a CAD workflow or the full upstream suite.
The script needs no window manager because it does not test window policy.
Upstream Tk's complete test suite has additional window-manager requirements.

## Virtual X11 display

The canonical pkgsrc `x11/modular-xorg-server` 21.1.24 package includes `Xvfb`.
Use the complete provider with its default `inet6 dri` options. These retain
DRI, DRI2, DRI3, GLX and Present. Glamor remains enabled when Mesa provides EGL.
Do not disable these features to obtain the virtual-display contract.
`Xvfb` needs no physical framebuffer or GPU for this contract.

The package declares runtime dependencies on `xkbcomp` and `xkeyboard-config`.
Its `MESSAGE` additionally specifies the minimum core-font packages:

| Package | Expected archive for the pinned source selection |
| --- | --- |
| X server | `modular-xorg-server-21.1.24.tgz` |
| XKB compiler | `xkbcomp-1.5.0.tgz` |
| XKB data | `xkeyboard-config-2.48nb1.tgz` |
| Font aliases | `font-alias-1.0.6.tgz` |
| Fixed core fonts | `font-misc-misc-1.1.3.tgz` |
| Core cursor font | `font-cursor-misc-1.0.4.tgz` |

The full `modular-xorg-fonts` metapackage is the server's recommended font set.
Keep the normal recursive package dependency closure. It includes X11,
Xfont2/fontenc, Pixman, libxcvt, libpciaccess, Mesa, libepoxy, libdrm and
libxshmfence providers. The final package metadata and target loader determine
the exact runtime closure. This table is a source inventory, not package or
runtime acceptance evidence.

Start an unused display as the same ordinary user that runs the contract:

```sh
/usr/pkg/bin/Xvfb :99 -screen 0 800x600x24 -nolisten tcp \
    > /absolute/xvfb.log 2>&1 &
xvfb_pid=$!
```

Use the supervising runner to wait for a successful X11 client request.
Inspect the server log if the request fails. The contract itself opens the
display and verifies mapped X11 windows. Stop only the server that this run
started, using the saved PID, after the contract exits. Do not remove another
server's display lock or socket. Preserve the exit status and server log.

Target `xkbcomp` is a runtime executable. It must be included in the guest.
The common cross `xkeyboard-config` recipe separates its optional test
executable from build-time data generation. Font generation uses native
`bdftopcf` and `ucs2any` tools. The target X server and all target libraries
must still use the common GCC16 cross compiler.

## Validation boundary

The source-only preparation uses native Tcl 9.1.0 to compile this script's
procedures and to verify usage and missing-display refusals. Native ZipFS
also reads `tk_library/tk.tcl` from the actual target shared library.
There is no native Tk 9.1 or Xvfb in that preparation. The positive GUI
contract therefore remains unrun until an installed target or a complete
native GCC16 Tk/X11 environment executes it. Record package hashes, the
selected shared library, server identity, exit status and current output.
