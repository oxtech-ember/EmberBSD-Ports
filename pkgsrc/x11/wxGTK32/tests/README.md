# GTK4 WebView contract

The shared `patch-gtk4-webview` keeps wxWidgets 3.2.12 public WebView APIs and
selects WebKitGTK 6.0 for the GTK4 toolkit. GTK3 retains its WebKitGTK 4.1 path.
The GTK4 path uses `evaluate_javascript`, `JSCValue` and the API6 context-menu
signal. `wxJSScriptWrapper` still controls JavaScript result/error conversion.
Script-message channels retain object JSON conversion and unregister their
signal handlers before re-registration. Gio, resolver and TLS failures retain
useful wx navigation error categories with libsoup3.

WebKitGTK 6 removed WebKitDOM. Selection, selected HTML, page text and deletion
therefore use equivalent DOM JavaScript in the private `wxWidgets.DOM` world,
so page overrides cannot replace these internal DOM operations. Public RunScript
continues to evaluate in the normal page world.
The old private D-Bus web-process extension is neither built nor installed for
GTK4. No public WebView function is disabled. Clipboard/editing, history,
printing, custom URI handlers, zoom and fullscreen retain their WebKit calls.
The GTK4 widget has native scrolling and does not need a GtkScrolledWindow.

Primary references:

- [WebKitGTK API6 migration](https://github.com/WebKit/WebKit/blob/webkitgtk-2.54.2/Source/WebKit/gtk/migrating-to-webkitgtk-6.0.md)
- [GTK4 migration](https://docs.gtk.org/gtk4/migrating-3to4.html)
- [WebKitWebView API source](https://github.com/WebKit/WebKit/blob/webkitgtk-2.54.2/Source/WebKit/UIProcess/API/glib/WebKitWebView.h.in)
- [User content manager API source](https://github.com/WebKit/WebKit/blob/webkitgtk-2.54.2/Source/WebKit/UIProcess/API/glib/WebKitUserContentManager.h.in)

Use the normal Ports-patched wxWidgets source tree and selected host tools:

```sh
python3 tests/webkit-selection.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --cmake /native/bin/cmake --work-parent /work/tmp
```

This executes the actual generated configure WebKit block with a controlled
pkg-config response, then the actual CMake find module. Seven cases cover API6,
refusal when only API4.1 is present, missing API6, GTK3, both CMake API variants,
and missing JavaScriptCore. Fixture libraries are metadata inputs, not compiled
libraries. The unpatched 3.2.12 configure fails the first GTK4 case.

Build the GUI contract against the selected SDK, installed GTK4 wxWidgets and
WebKitGTK 6.0. Supply the usual toolchain and target pkg-config settings when
cross-compiling; no target executable is run by configure.

```sh
cmake -S tests -B /work/wx-webview-test \
  -DwxWidgets_CONFIG_EXECUTABLE=/sdk/bin/wx-config
cmake --build /work/wx-webview-test
```

Run `webkit6-contract` on the matching host/target with a real GTK4 display,
WebKit web-process sandbox and its ordinary runtime dependencies. It uses local
HTML and vetoes its only URL navigation before any network request. It checks
object/Unicode/null/undefined results, asynchronous exceptions and client data,
message registration/re-registration, empty/collapsed/nonempty selections,
selected markup, deletion, page source/text, context-menu ABI and Gio errors.
A 30-second internal timeout exits unsuccessfully. Printing, clipboard access,
real network/TLS failures and process-swap navigation still require application
acceptance; this contract does not claim to exercise them.

The metadata regression passes on the selected host tools. Full WebView
translation-unit compilation, GUI runtime and memory checking await the shared
GTK4/WebKitGTK target build; preparation of this test is not runtime acceptance.

# GTK4 text and spellchecking contract

`patch-gtk4-text` adapts GtkEntry/GtkTextView without disabling spellchecking.
It uses the existing GTK4 native IM contexts, GtkText's native edit batching,
and GtkTextBuffer user-action signals. A shared native-im helper observes the
native widget's key controllers, refs their existing context for synchronous
filtering inside wxWindow's current-key scope, and preserves the controller's
`im-update` signal when handled. The capture handler consumes handled keys;
unhandled keys continue through native dispatch. No second IM context is
created. The temporary controller model is released before filtering; the
widget, controller and context remain referenced across synchronous callbacks. Clipboard signals/actions operate on the
GtkEditable delegate. Completion observes its GTK4 popover map/unmap signals.
Text geometry uses the public GtkAccessibleText interface, and style queries
read public GtkTextTag properties in priority order. Scrollbars use the shared
GTK4 wxWindow adjustment implementation supplied by `patch-gtk4-core`.

The current stable libspelling 0.4.10 TextBufferAdapter requires GtkSourceBuffer.
Multiline controls create that buffer directly. Singleline entries synchronize
text and cursor/selection with a short GtkSourceBuffer and reuse the same
adapter for checking, language selection and correction actions. Its error tag
becomes Pango error underlines on the entry. Corrections flow back through
wxTextCtrl's normal SetValue/event contract. There is one spelling engine and
no duplicated dictionary parser or new GTK3 dependency. The supported API comes
from [libspelling 0.4.10](https://gitlab.gnome.org/GNOME/libspelling/-/tree/0.4.10),
not the development documentation's newer API.

```sh
python3 tests/spelling-selection.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --work-parent /work/tmp
```

Five actual generated-configure cases pass: GTK4/libspelling, GTK4 refusing
GTK3 gspell, missing libspelling, preserved GTK3 and explicitly disabled feature.
The unpatched recipe's GTK4 case fails. GTK4 spellchecking requested but missing
libspelling is a configure error, including in the optional CMake build.

`text4-contract` is built by the same tests CMake project. It can be built before
WebKit with `-DBUILD_WEBKIT_CONTRACT=OFF`. Run it on the matching GTK4 target with
an Enchant `en_US` dictionary installed. It tests native singleline and multiline
selection replacement, separate edit event counts, suppressed programmatic
updates, Unicode offsets, length boundaries, style round trips, real misspelling
underlines, correction actions, and disabling spellchecking. Its timeout fails
if the display, dictionary or checker cannot complete the operation. The native
insert-at-cursor checks do not simulate IME composition. Input acceptance must
exercise composed commits in both controls: one text change and wxEVT_CHAR for
each committed Unicode code point, including a commit delivered after the
capture key handler has cleared m_imKeyEvent. Clipboard, completion popup
keyboard interaction and memory checks also remain separate acceptance tasks. This fixture and text translation units are prepared
but have not yet been compiled or executed against the shared GTK4 target stack.

# GTK4 application and event loop contract

`patch-gtk4-evtloop` replaces removed GTK main-loop APIs with one GLib main loop
per wx loop. An exit request for an outer loop does not terminate a nested
modal loop. Default-context wakeups, timeouts and wx FD sources remain shared.
GdkSurface event/layout signals re-arm the existing one-shot idle source;
GtkWindow `notify::is-active` and the toplevel list model track application
activation. Cleanup disconnects observers and removes hooks and idle sources.
GTK4 widget operations remain on the main thread; queued wx events and idle
wakeups provide the supported worker-thread path.

Selective native `YieldFor(mask)` currently returns false before dispatching
anything, with one diagnostic per process. GTK4 removed the global GDK event
handler used by GTK3. Temporarily blocking Surface signal handlers from an
emission hook is unsafe for nested emissions: it can also suppress remaining
handlers of the outer emission. This implementation does not use that approach.
Ordinary `Yield()` and `YieldFor(wxEVT_CATEGORY_ALL)` dispatch pending native and
wx events normally. Consumers requiring selective yielding need further GTK4
integration; this boundary is not full KiCad runtime acceptance.

The method-level regression compiles the actual prepared event-loop and idle
methods against the selected native GLib/GObject. Its harness supplies wx base
lifecycle callbacks and a GObject with the same idle-signal declarations. It
checks nested exit ordering, loop reuse, an exit before DoRun, timeout source
cancellation, worker wakeup without wxApp, selective-yield refusal, full yield,
one-shot idle hooks, nested idle/modal processing and stored-exception cleanup.
It does not substitute for compiling the complete wx/GTK translation units or
checking real GTK activation, native events and frame rendering.

```sh
python3 tests/evtloop-glib.py --source /prepared/wxWidgets \
  --cxx /native/bin/clang++ --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

Pass any selected host ABI/compiler flags using repeated `--cxx-flag=...`.
The test runs native output only and treats GLib critical diagnostics as fatal.
No target program is executed on the build host.

# GTK4 GLCanvas contract

`patch-gtk4-glcanvas` uses real EGL contexts and pbuffer drawables with GTK4
snapshot presentation. `SetCurrent(canvas)` binds the requested native context
to that canvas, including switching one context between canvases. Desktop GL
uses a compatibility profile by default, preserving KiCad's immediate-mode GL
and framebuffer-zero contract. GLES is an explicit context request. EGL 1.5,
libepoxy and a GTK display using EGL are required; a GLX-only display produces
an error. There is no hidden GDK debug switch or CPU pixel readback in this
presentation implementation.

Framebuffer zero is the native pbuffer. It is **single-buffered**:
`GL_DOUBLEBUFFER` is false even when wx `DoubleBuffer()` is requested. Mesa
supports `GL_BACK` / `GL_BACK_LEFT` on a pbuffer by mapping them to its front
storage. Presentation has separate buffers: `SwapBuffers()` copies the rendered
frame into a new immutable GPU texture and publishes it to GTK; further GL
rendering does not alter the displayed frame. This is not a native double-buffer
framebuffer or a window-system `eglSwapBuffers` operation. Stereo, overlays,
auxiliary buffers and accumulation buffers are rejected explicitly.

The bridge shares GTK's display-wide resource group. Contexts have distinct
native identities and independent GL state, but **resource isolation is not
provided**, including when the wx context constructor receives no `other`
context. Explicit sharing validates display and client API compatibility.
Completed textures and fences remain alive while GTK retains their snapshots,
even after canvas/context destruction. Worker-thread texture release queues a
GLib idle source; GL deletion occurs on the UI loop, never via an inline-capable
`g_main_context_invoke` call.

Presentation textures use ordinary RGBA storage tagged with GDK's sRGB color
state. Desktop blits disable sRGB conversion while copying stored encoded
values, bypass caller pixel-transfer state, and preserve scissor, framebuffer,
texture, unpack-buffer and sRGB state. GLES uses `CopyTexSubImage2D`, which also
copies stored values and has no legacy pixel-transfer state; it avoids the
sRGB-format matching restriction of `CopyTexImage2D`. An sRGB texture format
would decode values again during GTK sampling and is deliberately not used.
The EGL sRGB framebuffer option still controls application rendering normally.

Primary implementation references:

- [Mesa pbuffer config selection](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.6/src/egl/drivers/dri2/egl_dri2.c)
- [Mesa BACK-to-FRONT pbuffer mapping](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.6/src/mesa/main/buffers.c)
- [Mesa copy validation](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.6/src/mesa/main/teximage.c)
- [Mesa copy color formats](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-26.2.6/src/mesa/state_tracker/st_cb_texture.c)
- [GTK shared GL texture import](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gsk/gpu/gskglframe.c)

```sh
python3 tests/gl4-selection.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --work-parent /work/tmp
python3 tests/gl4-release-glib.py --source /prepared/wxWidgets \
  --cxx /native/bin/clang++ --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

The first check executes actual generated-configure logic for EGL 1.5/epoxy,
missing dependencies, explicit EGL disable, and preserved GTK3 selection. The
second compiles the production release-dispatch function against native GLib;
its worker releases a frame while the main context is unowned. Replacing the
queued idle source with `g_main_context_invoke` makes this regression fail.
Use repeated `--cxx-flag=...` for selected host ABI/compiler flags.

Build `gl4-contract` using the same CMake project and selected SDK, optionally
with `-DBUILD_WEBKIT_CONTRACT=OFF -DBUILD_TEXT_CONTRACT=OFF`. Run on the matching
GTK4/EGL target. It checks native context identity, display-wide/explicit sharing,
FB0, the single-buffer limitation and KiCad BACK readback, immutable presentation,
vertical orientation, retained-frame lifetime, resizing, sRGB values and caller
GL state preservation. Hardware GL is required by default. Explicit
`WX_GL_ALLOW_SOFTWARE=1` permits a software-only recovery/CI environment and does
not establish hardware acceptance. Full translation-unit compilation and this
GUI fixture remain pending the shared GTK4 build; method/metadata checks do not
claim that runtime acceptance.

# GTK4 menu contract

`patch-gtk4-menus` implements menubar and popup menus with public GTK4 APIs.
`GMenuModel` sections supply separators and custom slots to `GtkPopoverMenu`;
owned `GtkButton`, `GtkCheckButton` and `GtkMenuButton` rows supply labels,
mnemonics, bitmap-bundle icons and wx highlight events. Stateful `GSimpleAction`
objects keep check/radio state and command delivery shared between rows and
keyboard shortcuts. Consecutive radio runs are regrouped on structural changes,
including removing a separator. Programmatic checks do not emit commands.
Labels and icons change on existing rows; structural mutation preserves row
identity and focus, and restores open submenus without duplicate wx open events.

The menubar uses public `GtkMenuButton`s in a `GtkBox`. GTK4's generated
`GtkPopoverMenuBar` top items do not bind sensitivity, and its generated menu
rows do not expose their tracker action via `GtkActionable:action-name`. Using
owned widgets preserves `EnableTop`, per-item highlight events and icons without
reading private GTK tracker data or depending on `GtkModelButton` internals.
GTK handles popover focus, Escape and mnemonic activation. Controllers add
submenu directional navigation, adjacent top menus and F10 menubar focus.
`GtkShortcutController` models own primary and extra accelerators; disabling,
removing or detaching a menu prevents their dispatch, and changing a label
replaces its primary accelerator.

`window_menu4.inc` provides the GTK4 `wxWindowGTK::DoPopupMenu` body. Include it
instead of the legacy GTK popup block. It delegates to
`wxMenu::GTKPopup(invokingWindow, anchorWidget, x, y)`. The custom wxPizza parent
must call `gtk_popover_present()` for its direct GtkPopover children during
allocation; GtkMenuButton manages its own submenus. Popup waiting uses the
existing active wx event loop's `DispatchTimeout`, with `wxEventLoopGuarantor`
for calls made before a loop exists. It returns synchronously after closure,
invoking-window/menu destruction or an event-loop exit request. RAII retains GTK
objects and releases/reparents the popover on exit. The common
`wxMenuInvokingWindowSetter` now uses the existing `wxWeakRef` API on all backends,
so returning after an event handler deletes the menu does not dereference it.

Primary references:

- [GtkPopoverMenu custom slots and keyboard behavior](https://docs.gtk.org/gtk4/class.PopoverMenu.html)
- [GtkShortcutController](https://docs.gtk.org/gtk4/class.ShortcutController.html)
- [GSimpleAction state and activation](https://docs.gtk.org/gio/class.SimpleAction.html)
- [GTK4 menu row creation](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gtk/gtkmenusectionbox.c)
- [GTK4 generated menubar ownership](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gtk/gtkpopovermenubar.c)

Build `menu4-contract` through the shared tests CMake project. Other contracts
can be deselected using their `BUILD_*_CONTRACT` options. The fixture invokes
real registered GTK shortcut actions and native row activation, checks dynamic
labels and accelerator replacement/removal, disabled top/item states, radio
regrouping, popup command/open/close behavior and destruction during a popup
command. Run it under ASan on a supported target to exercise the former common
RAII use-after-free. Actual key delivery, mouse hover, nested menu keyboard
navigation, rendered icons, RTL and application shutdown remain GUI acceptance
checks; programmatic shortcut activation is not synthetic keyboard evidence.

Source-only Cppcheck 2.22.0 reports no warnings in the new implementation and
fixture. Patch application uses zero fuzz. Full translation-unit compilation,
the runtime fixture, Clang analysis and executable memory checking remain
pending the shared GTK4 build; these prepared checks are not runtime acceptance.
