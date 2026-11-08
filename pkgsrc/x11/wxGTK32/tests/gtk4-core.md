# GTK4 window integration

The Unix provider is being moved to GTK4, WebKitGTK 6.0 and libspelling.
Darwin continues to use Cocoa. The package path names wxWidgets 3.2, not a
GTK major version. GTK4 integration is in progress and does not yet produce
a working GTK4 wxWidgets or KiCad package.

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
without requesting continuous animation. The container, settings, theme
renderer, dialog, scroll helper and scrollbar translation units pass target
Clang syntax compilation with GTK 4.24.1 source/generated headers and a real
configured wxWidgets setup. Library linking and GUI/runtime acceptance remain
pending; this check does not establish a working wxWidgets package.

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

`patch-gtk4-style` obtains theme colours and dimensions from cached native
GTK widgets. Scoped contexts restore their state after rendering. Text
selection uses named theme colours because GTK4 does not expose the textview
selection CSS node as a widget. Frame-decoration metrics use the X11 window
manager property when available; unknown server decorations on Wayland report
an unavailable metric. GTK4 widgets always use buffered GSK rendering.
`style4-contract.cpp` exercises theme changes, native font/metrics and scoped
button/check/radio rendering through the public wx renderer. It passes target
syntax compilation; its real-display runtime check is still pending.

The combined patches pass zero-fuzz application to the verified upstream
3.2.12 release. Full backend compilation, linking, runtime and memory checks
remain required. Do not publish a wxWidgets binary
based only on patch-application or metadata tests.

`patch-gtk4-art` resolves GTK4 icon-theme paintables and rasterizes their immutable
snapshots for wxArtProvider, including theme-coloured symbolic icons. It retains
provider fallback for unknown names and expands scalable sources into usable
icon-bundle sizes. Its complete target translation unit passes syntax checks;
real-display icon rendering is covered by the pending `style4-contract` run.

GTK4 mini-frames use the shared native utility-window implementation for
parent ownership, close/resize handling and client-area measurements. Their
caption appearance follows the desktop theme/window manager; the previous
hand-painted small caption is not reproduced pixel for pixel. The top-level
fixture includes a mapped mini-frame and checks its parent, client size and
native capabilities; real-desktop execution remains pending.

`patch-gtk4-filechooser` keeps native GTK file/directory dialogs and embedded
file controls, using GFile/GListModel ownership and the common GTK provider's
per-instance hidden-file/overwrite properties. Preview and extra controls use
the dialog content box. GTK4 pickers use GtkButton and the existing wx native
dialog workflow, including directory creation and modal parent lifetime.
Non-local selections are rejected by dialogs because wx path APIs represent
local filesystem paths. No portal/private chooser fields are used.

`filechooser4-contract.cpp` checks native property propagation, filter
replacement, native overwrite acceptance/confirmation, asynchronous selection,
coalesced-notification disposal, desktop hidden-file preference isolation, picker
labels and destruction of a parent during a picker modal loop. Run its
`interactive` mode to inspect preview, save-overwrite confirmation and directory
creation on a real display; interactive observations are not automatic PASS.
The five affected wx translation units, the shared GTK producer's two C units,
and the fixture pass target syntax compilation. GUI, memory-check and package
acceptance are pending the shared GTK4 build, including preference isolation
and preview/extra-control layout under the actual theme.

`about4-contract` covers native about-window metadata and paintables, reuse of
an open window, normal/compositor close, and direct native destruction while
another reference delays disposal. The full target translation unit and fixture
pass syntax compilation, and Clang Static Analyzer reports no diagnostics.
Cppcheck cannot parse the target system headers in either the upstream or
modified translation unit; this is not a successful Cppcheck check. Executable
GUI and memory checks require the completed GTK4 wxWidgets library.

GTK4 uses the existing `wxGenericCalendarCtrl` on the common wx GTK4 window and
drawing implementation. It keeps date ranges, month locking, week styles and
activation without relying on removed GtkCalendar properties or signals.
`calendar4-contract` checks leap-day/range handling, silent programmatic updates,
keyboard month locking/navigation, marks and double-click dispatch after mapping.
This fixture does not replace real pointer-input, theme or accessibility checks;
linked GUI execution remains pending the complete wxWidgets package.

Native message dialogs, page setup and assertion dialogs use one GTK4 modal
adapter backed by the existing wx GUI event loop. It retains native objects,
restores modality, and stops on response, close, hide or removal of the dialog
or parent from GTK's public toplevel registry. Responses arriving before the
loop starts or while another dialog is nested are retained. Raw native dialog
owners clean up on exceptions as well as normal return. Assertions retain
backtrace expansion, saving, clipboard copying and continue/suppress actions.

`GtkPrintOperation` remains the GTK printing provider, including its native
operation lifecycle. Both configure and CMake select `gtk4-unix-print`; the
actual diagnostic configure enables `wxUSE_GTKPRINT`, rather than overriding
a setup macro for an empty translation-unit check. Message-dialog always-on-top
requests share the existing mapped X11 EWMH implementation with top-level
windows; Wayland has no equivalent public request.

`modal4-contract.cpp` exercises early and nested responses, Help/Cancel/close,
direct native destruction, wx owner/parent destruction, destruction from a
modal-property notification, page-setup acceptance/cancellation, assert
suppression and native print cancellation without submitting a print job.
The five affected full translation units and fixture pass target syntax
compilation. Clang static analysis reports no finding in the changed paths;
two diagnostics in unchanged wx string-buffer code were inspected against its
reference-counted copy semantics. Runtime, sanitizer, visual assertion layout,
backtrace save/copy and actual printed/PDF output acceptance remain pending the
linked GTK4/wxWidgets package and target display.
