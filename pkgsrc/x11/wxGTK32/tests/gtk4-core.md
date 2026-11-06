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
3.2.12 release. C++ compilation, runtime and memory checks are pending the
shared GTK4 target build. Do not merge the provider switch or publish a
wxWidgets binary based only on patch-application or metadata tests.
