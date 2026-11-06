# GTK4 window integration

The Unix provider is being moved to GTK4, WebKitGTK 6.0 and libspelling.
Darwin continues to use Cocoa. The package path names wxWidgets 3.2, not a
GTK major version. This branch is an integration draft and does not yet
produce a working GTK4 wxWidgets or KiCad package.

`patch-gtk4-pizza` implements the client container using `GtkWidget`
measurement, allocation and snapshot callbacks. GTK owns CSS rendering and
the content inset. wxWidgets owns child geometry, scroll offsets and RTL
placement. Child removal and container disposal release coordinate records
and GTK references. Virtual extent is a natural size, so it does not impose a
minimum viewport size. Explicit wx tab order is implemented by the widget's
focus vfunc. Freeze retains immutable GSK snapshot nodes; thaw requests a new
frame. Native children have individual retained nodes, released on unparent.

`patch-gtk4-window` adds opaque key-event access, capture controllers scoped
to the nearest wx owner, pointer gestures and adjustment notifications shared
by window scrollbars and `wxScrollBar`. It connects `wxScrollHelper` to the
container's virtual extent. Native size notifications observe completed frames
without requesting continuous animation. These changes are still uncompiled;
the rest of the window, input, rendering and GL integration is in progress.

Ordinary wx child windows expose their actual `GtkNative` surface through
`GTKGetSurface()`, rather than pretending every child owns a GdkWindow.
Client/screen conversion uses GTK widget transforms and the surface transform.
X11 uses real desktop coordinates; Wayland exposes coordinates relative to its
toplevel because the compositor does not provide a desktop origin. Pointer
warping is implemented for X11 and explicitly unsupported on Wayland.

The container emits `wx-size-allocate(width, height)` with GTK content dimensions,
`wx-paint(cairo_t*)`, then `wx-snapshot(GtkSnapshot*)` before its children.
`m_inSnapshot` covers that snapshot call so a GL swap during a paint event can
provide a texture without recursively requesting another frame.

`patch-gtk4-dc` routes `wxPaintDC` through the active snapshot Cairo context.
Outside paint, `wxClientDC` and `wxWindowDC` use the latest wxPizza client
content node as the Cairo destination. GTK renders that node to a texture and
downloads it to a mutable image buffer; the next snapshot installs the changed
content node in the same layer, before children. This rare immediate path uses
a CPU readback. If the widget has no prior snapshot or is a native control, the
existing generic offscreen context remains available for measurement, without
claiming screen output. This path does not read other windows or the desktop;
transparent client content backed by a parent's pixels still needs validation.
GTK4 has no desktop surface for `wxScreenDC`, so that API reports unsupported.
Bitmap textures copy pixels into immutable
`GdkMemoryTexture` generations because retained snapshots can outlive later
writes to a `wxBitmap`. Textures for bitmaps with exposed writable pixel data
or a mutable Cairo surface refresh on each snapshot.

`patch-gtk4-controls` adapts buttons, checkboxes, radio buttons, labels, choices
and combo boxes. GTK4 removed GtkComboBox's multi-column popup API; `SetColumns`
with more than one column reports an unsupported operation. Existing upstream
control tests must run against the resulting package before acceptance.

`gtk4-pizza.cpp` exercises the actual container with a real GTK4 display:
allocation, painting, freeze/thaw, CSS border, scrolling, RTL, virtual extent, external
unparenting and disposal. Compile it together with the patched
`src/gtk/win_gtk.cpp`, using the selected SDK and the actual configured
wxWidgets include/defines and GTK4 pkg-config flags. Run with
`G_DEBUG=fatal-warnings`. Display absence is a failure, never a passing test.
This component test does not establish wxWindow, GPU or KiCad acceptance.

The container patch passes zero-fuzz application to the verified upstream
3.2.12 release. GTK4 DC/bitmap changes and the combined backend still need
compilation, runtime and memory checks. Do not publish a wxWidgets binary
based only on patch-application or metadata tests.
