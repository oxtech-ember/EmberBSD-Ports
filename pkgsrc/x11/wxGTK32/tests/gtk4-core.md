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
minimum viewport size.

`patch-gtk4-window` introduces genuine opaque key-event access and a common
scrollbar adjustment boundary. It connects `wxScrollHelper` to the container's
virtual extent. The rest of the window, input, rendering and GL integration
is still being implemented; these changes are not a completed backend.

`gtk4-pizza.cpp` exercises the actual container with a real GTK4 display:
allocation, painting, CSS border, scrolling, RTL, virtual extent, external
unparenting and disposal. Compile it together with the patched
`src/gtk/win_gtk.cpp`, using the selected SDK and the actual configured
wxWidgets include/defines and GTK4 pkg-config flags. Run with
`G_DEBUG=fatal-warnings`. Display absence is a failure, never a passing test.
This component test does not establish wxWindow, GPU or KiCad acceptance.

The container patch passes zero-fuzz application to the verified upstream
3.2.12 release. C++ compilation, runtime and memory checks are pending the
shared GTK4 target build. Do not merge the provider switch or publish a
wxWidgets binary based only on patch-application or metadata tests.
