# Incremental Autoconf builds

The Autoconf recipe uses the selected native bmake, with no GNU make dependency.
Bakefile's shared dependency emitter reads compiler depfiles for bmake through
`.ALLTARGETS` and optional includes. It covers every generated makefile, including
wxrc, samples and tests. The historical `IF_GNU_MAKE` substitution is an include
prefix; for bmake it emits the common include loop and comments out the original
GNU wildcard include. Upstream's GNU make branch remains supported. The CMake
option keeps its existing build-system selection.

Previously, Bakefile generated `.deps/*.d` but ignored them with bmake, allowing
an object to survive a change to its included GTK4 implementation. The regression
uses the real Autoconf macro and three generated makefile contexts, checks the
shipped configure against the macro, and proves that only changed headers trigger
rebuilds. Nested object paths and a first build without depfiles are covered.
The previous producer fails this regression. A dry run with the actual wx makefile
accepts the bmake include loop and preserves the already updated GL canvas object.
Keep dependency files along with compatible objects.

The normal aarch64 SDK install of `wxGTK32-3.2.12nb18` passed with bmake.
It reused 225 packages, downloaded none, and preserved the compiled C++ objects.
The staged `make` resolved to native bmake; the old gmake wrapper was removed.
The generated makefiles retained 743 compiler dependency files. This package
build does not establish GUI runtime acceptance.

```sh
python3 tests/bmake-dependencies.py --source /prepared/wxWidgets \
  --bmake /native/bin/bmake --autoconf /native/bin/autoconf \
  --shell /native/bin/mksh
```

# GTK4 AUI and top-level window hints

`patch-gtk4-window-hints` draws AUI sashes through the existing native splitter
renderer, clipped to the requested AUI rectangle. The GTK4 hint frame uses the
common top-level opacity path instead of GTK3 popup/shape calls. Its placement
remains subject to the window system, including Wayland compositor policy.
The splash window requests its X11 EWMH type through the shared window-state
helper before mapping; the common top-level mapper uses that request before
the ordinary dialog/utility/normal default. On Wayland the unsupported type
hint returns false and normal wx top-level behavior remains; no native Wayland
splash or transient role is claimed.

```sh
python3 tests/window-type-gtk4.py \
  --source /prepared/wxWidgets/include/wx/gtk/private/windowstate4.h \
  --cxx /native/bin/clang++ --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

The fixture extracts the actual request/getter functions and uses native
GObject qdata, mocking only GTK display/mapping boundaries. Native ASan/UBSan
passes X11 copying/replacement, absent defaults, Wayland refusal and invalid or
already-mapped requests. The previous guard fails the empty-string case.
Use repeated `--cxx-flag` arguments for the diagnostic flags shown below.
This fixture does not simulate a window manager or rendered sash.
All four changed target TUs pass syntax checks. Clang analysis is clean for
dockart, splash and toplevel; framemanager retains one unrelated, unchanged
`OnPaneButton`/assertion path to `p.window->SetSize`. Cppcheck 2.22 was interrupted
after a bounded run on the first TU without producing diagnostics, so its
analysis of this group is incomplete. Real AUI dragging, opacity and splash
window-manager behavior remain GUI acceptance work.

# GTK4 font picker and API declarations

`patch-gtk4-fontpicker` uses an asynchronous GtkFontDialog and a normal GtkButton.
This keeps the full font chooser independent of the wx label styles: the label
can show only the family or the complete style/fractional-size description, and
can optionally use the selected font. Pending requests are cancellable, use
weak native/wx owners, and prevent duplicate dialogs. Label updates hold both
button and label across property notifications; callbacks recheck the wx owner
before sending the selection event. Programmatic updates send no picker event.

```sh
python3 tests/fontpicker-gtk4.py --source /prepared/wxWidgets/src/gtk/fontpicker.cpp \
  --cxx /native/bin/clang++ --work-parent /work/tmp
```

The extracted production helpers and methods pass native ASan/UBSan with
mocked GTK/GObject and wx lifetime boundaries. Cases cover success, cancellation,
duplicate activation, late completion, reentrant owner destruction, a detached
child label, both label styles and programmatic updates. Use repeated
`--cxx-flag` arguments for diagnostic flags, as in the Cairo fixture below.
This is not real GTK dialog, font selection or native GObject leak acceptance.
Target syntax and Clang analysis pass. Cppcheck 2.22 completed before the final
label-reference-only change, reporting standard GTK cast macros and an existing
asserted-font null-check pattern, with no actionable source finding. The final
ownership delta is covered by the lifetime fixture and Clang analysis.

The text-entry declaration patch exposes GTK4's opaque `GdkEvent` type without
including GTK headers in the public interface. The taskbar patch only corrects
the existing GTK4 stub's `wxBitmapBundle` signature. Upstream GTK4 tray support
remains unavailable; no StatusNotifierItem implementation is claimed. Both
actual target translation units pass syntax checks.

# GTK4 Cairo contexts and media presentation

`patch-gtk4-window-cairo` routes window graphics contexts through the existing
wxClientDC/wxPizza drawing owner. The DC stays alive until its referencing Cairo
context is released. Measuring contexts use a one-pixel Cairo image and font
scaling uses the shared Pango context. The exported private widget-owner lookup
is shared with input dispatch.

For `CreateContextFromNativeWindow`, the GTK4 native handle is `GdkSurface*`.
wx-owned GTK surfaces use that same DC path; a foreign GtkNative surface is
refused instead of detaching its GSK renderer. A raw surface without GtkNative
must be exclusively owned by the caller. Only that explicit raw-surface path
uses GDK's supported, deprecated Cairo frame API, pairing begin/end on success
and failure. This is not an API for drawing over arbitrary GTK widgets.

```sh
python3 tests/cairo-gtk4.py --source /prepared/wxWidgets/src/generic/graphicc.cpp \
  --wx-source /prepared/wxWidgets --cxx /native/bin/clang++ \
  --pkg-config /native/bin/pkg-config --work-parent /work/tmp
```

The fixture extracts production constructors, factories, initialization and
destruction, with real Cairo/Pango/GLib and the actual wx ownership templates.
GDK frames and wxWindow/DC boundaries are mocked. It checks frame pairing,
failed context cleanup, GTK renderer ownership, parent fallback, DC lifetime,
measuring dimensions and explicit/default font resolution. The initial owner
route fails its unavailable-DC case; the corrected factory returns null.
Strict native ASan/UBSan passes with repeated `--cxx-flag` arguments:
`-fsanitize=address,undefined`, `-fno-sanitize-recover=all`,
`-fno-omit-frame-pointer`. Target syntax passes for graphicc and window.cpp.
Full-TU Clang analysis reports five paths in unchanged font/string-buffer and
user-dash code, with none in the GTK4 adapter; it is not a zero-finding result.
Cppcheck 2.22 cannot parse the actual target-preprocessed `sys/endian.h` input.
Real GUI composition and raw-surface execution remain separate checks.

`patch-gtk4-media` retains the shared GstPlayer backend, including playback
rate, seeking, audio and media events. Its public video-renderer interface uses
the common gst-plugins-base appsink. Streaming callbacks copy validated RGBA
rows into a bounded latest-frame mailbox; a queued GSource delivers frames to
the UI context, where GdkMemoryTexture is drawn by the existing wx-snapshot
signal. This is a CPU frame copy, not a zero-copy or hardware-decoding claim.
The mapped span is checked independently of GstVideoMeta's stride and offset.
Detach cancels pending delivery and releases GTK resources on the UI context.

```sh
python3 tests/media-gtk4.py --source /prepared/wxWidgets/src/unix/mediactrl_gtk4.inc \
  --cxx /native/bin/clang++ --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

The actual presentation methods pass strict native ASan/UBSan with the same
diagnostic flags, real GLib/GObject, and mocked sample/drawing boundaries.
Cases include worker-to-UI delivery, latest-frame coalescing, stride packing,
preroll, invalid caps/maps, truncated and overflowing spans, nonzero offsets,
detach, late callbacks, destroyed widgets and aspect-fit geometry. The fixture
rejects malformed and truncated mapped spans. The full target GstPlayer TU
passes syntax and Clang analysis. Cppcheck's target header/preprocessor limits
affect both baseline and candidate; it has no clean full-TU verdict.
Real decoding, audio, seek/rate, EOF and window integration still need runtime
acceptance with the common GStreamer plugins.

`patch-gtk4-glcanvas-header` uses GTK's real `GtkSnapshot` alias and includes
complete GTK types before the private implementation structs. The public wx
header remains usable without GTK include paths and alongside GTK headers.
Both header probes, the actual target GLCanvas TU and Clang analysis pass.
Cppcheck 2.22 cannot preprocess the actual Graphene ARM SIMD header, and its
Clang-import path asserts in `token.cpp`; these are analyzer limitations.
This header correction does not add GL rendering/runtime acceptance.

The GTK4 GL implementation leaves `wxGLApp` RTTI registration to the shared
`src/common/glcmn.cpp`, as the existing EGL/GLX ports do. Its former duplicate
registration failed the actual target shared-library link. Removing that one
registration, recompiling the GTK4 GL translation unit and relinking against
the same remaining objects succeeds; Clang analysis also passes. The
`InitGLVisual` implementation and Canvas/Context RTTI remain unchanged. The
previous Cppcheck Graphene parser limitation still applies. This link check
does not establish EGL rendering or context-lifetime acceptance.

# GTK4 status bar and checklist contract

`patch-gtk4-statusbar` draws the resize grip with the existing wxDC/theme pens
and starts native GDK toplevel operations from the event already owned by the
window dispatcher. The native device, button, surface coordinates and timestamp
are retained; unrelated surfaces or missing input cause the wx event to be
skipped. Logical grip coordinates mirror with the rest of wx's RTL content,
while the physical resize edge selects south-west or south-east. Pointer-emulating
touch can resize; right-button move keeps its actual native button number.

```sh
python3 tests/statusbar-gtk4.py \
  --source /prepared/wxWidgets/src/generic/statusbr.cpp \
  --cxx /native/bin/clang++ --work-parent /work/tmp
```

The regression extracts the actual helper, event handlers, grip rectangle and
paint method. Mock external calls check missing input, surface translation,
native event identity, touch, RTL hit geometry and in-bounds logical drawing.
Strict native ASan/UBSan execution passes with `--cxx-flag=-fsanitize=address,undefined`,
`--cxx-flag=-fno-sanitize-recover=all` and `--cxx-flag=-fno-omit-frame-pointer`.
The button-only candidate fails its touch case. Real pointer delivery, window
manager interaction and rendered pixels require the separate GUI acceptance.
The full status-bar TU passes target syntax and Clang Static Analyzer. Cppcheck
2.22 reports unchanged callback/cast/style warnings, the existing GTK-version
condition and inherited event-handler naming; none points into the new grip or
drag code. Its included wx header reports retain their earlier classification.

`patch-gtk4-checklist` adapts `GetItemHeight()` to GTK4's five-argument
`gtk_tree_view_column_cell_get_size` without the removed cell-area argument.
The original TU fails this API check in the actual target build; the patched
TU compiles against the selected GTK4 headers. The older-toolkit signature is
preserved in its existing upstream build branch.

The checklist TU passes target syntax checking and Clang Static Analyzer.
Cppcheck 2.22 reports the unchanged wx hash-map macro/`wxAny` header findings and
older casts outside the changed getter; no new finding points into the adapted
call. GTK4's existing TreeView APIs still emit deprecation warnings.

# GTK4 Unix utilities contract

`patch-gtk4-utilsx11` uses GTK4's keyboard device state, matches X11 window
manager queries to their supplied display, and uses the shared GIO URI launcher.
The launch context follows the top-level window's display, falling back to the
default display when no window exists. The existing `wxGtkObject` owner releases
the context on both success and failure; failure reaches the existing browser
fallback. No new library or private launcher is introduced.

```sh
python3 tests/utilsx11-gtk4.py \
  --source /prepared/wxWidgets/src/unix/utilsx11.cpp \
  --wx-include /prepared/wxWidgets/include \
  --cxx /native/bin/clang++ --work-parent /work/tmp
```

The harness extracts the actual WM and keyboard functions and the URI function
up to its existing fallback boundary. Only external GTK/GDK/GIO/Xlib calls are
mocked; the production `wxGtkObject` template supplies ownership. It covers
absent devices, modifier and lock states, display selection, missing atom names,
URI success/failure and exactly-once resource release. It never launches a real
browser. Native ASan/UBSan execution passes; supply diagnostic flags with repeated
`--cxx-flag` arguments (`-fsanitize=address,undefined`,
`-fno-sanitize-recover=all`, `-fno-omit-frame-pointer`). Target compilation and
static analysis cover the full TU;
real GTK display, WM, browser and full wx GUI execution remain separate checks.

The target compiler reports three GTK X11 API deprecations in the hint
query, with those APIs still available in GTK 4.24. Cppcheck's
`dangerousTypeCast` at the timestamp call is a false positive: the existing
`wxGtkObject<T>::operator T*()` returns the same pointer type required by GDK.
Unchanged wx hash-map/`wxAny` header reports retain their earlier classification;
the full-TU Clang analyzer reports no finding in this change.

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
  -DwxWidgets_CONFIG_EXECUTABLE=/sdk/bin/wx-config \
  -DWX_SOURCE_DIR=/prepared/wxWidgets
cmake --build /work/wx-webview-test
```

The style, clipboard and overlay contracts use private headers. `WX_SOURCE_DIR`
must select the Ports-patched sources used to build the installed library.
Only those three targets receive this include directory. The other contracts
use installed headers. No source path is needed when these contracts are disabled.

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
GTK4 wxWindow adjustment implementation supplied by `patch-gtk4-window`.

The current stable libspelling 0.4.11 TextBufferAdapter requires GtkSourceBuffer.
Multiline controls create that buffer directly. Singleline entries synchronize
text and cursor/selection with a short GtkSourceBuffer and reuse the same
adapter for checking, language selection and correction actions. Its error tag
becomes Pango error underlines on the entry. Corrections flow back through
wxTextCtrl's normal SetValue/event contract. There is one spelling engine and
no duplicated dictionary parser or new GTK3 dependency. The supported API comes
from [libspelling 0.4.11](https://gitlab.gnome.org/GNOME/libspelling/-/tree/0.4.11),
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

# GTK4 top-level contract

`patch-gtk4-toplevel` implements the GtkWindow lifecycle on GTK 4.24 or newer.
A vertical `m_mainWidget` owns the expanding wxPizza client area; wxFrame places
its menu/status/tool bars around that area. Public GtkHeaderBar titlebars retain
caption button selection on both display backends. Actual allocation supplies
client and decoration sizes; an early explicit client size is corrected once
when those extents become measurable. Native state notifications drive wx
activation, iconize, maximize and fullscreen state.

`close-request` passes through wx close handling and veto without allowing GTK
to destroy a live wx owner independently. GTK 4.24 `force-close` hides the window,
sends a non-vetoable wx close event and schedules wx destruction. The explicit
`AddGrab` API uses the existing wx event loop plus GtkWindow modality and the
common window disabler; weak ownership and a retained native reference permit
destruction while its synchronous call is waiting. Native signals, X11 event
observers, configure idles and attention timers are disconnected on destruction.
Refresh delegates to the shared window implementation to invalidate retained
ClientDC contents.

On X11, the public `GdkX11Display::xevent` observer always returns false. A
coalesced idle reads geometry after GDK processes the native event, including
pure window-manager moves. ICCCM/Motif/EWMH requests implement positioning,
caption functions, tool-window/taskbar state, resize maxima/increments and
attention. Increment reset preserves only GTK's scale alignment; extra hints
are merged after GTK rewrites WM_NORMAL_HINTS and only changed properties are
written. Always-on-top is requested after native map, when the WM can handle it.

Wayland keeps the shared backend's toplevel-relative screen coordinates. Its
public GTK/GDK API does not expose global positioning, application-selected
always-on-top/taskbar state, non-activating attention, or arbitrary interactive
maximum/increment constraints. These requests are not reported as successful
native transitions. Minimum and programmatic size constraints still use GTK
measurement and wx size constraints. `ShowWithoutActivating` avoids an explicit
activation request; final focus policy belongs to the compositor. No private
GDK structures or substitute GTK3 window objects are used.

Primary references:

- [GtkWindow sizing and state](https://docs.gtk.org/gtk4/class.Window.html)
- [GtkWindow close veto](https://docs.gtk.org/gtk4/signal.Window.close-request.html)
- [GTK 4.24 force-close](https://docs.gtk.org/gtk4/signal.Window.force-close.html)
- [GdkX11Display event observation](https://docs.gtk.org/gdk4-x11/signal.X11Display.xevent.html)
- [GTK's CSD size and lifecycle implementation](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gtk/gtkwindow.c)
- [GDK X11 geometry hints](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gdk/x11/gdksurface-x11.c)

`toplevel4-contract` is built by the tests CMake project; select it with
`BUILD_TOPLEVEL_CONTRACT`. It requires a real desktop window manager/compositor,
not an unmanaged X server. The fixture exercises measured client size with
frame bars, size round trips, hide/show notifications, close disable/veto,
maximize/fullscreen/minimize restoration, nested grabs, synchronous owner
removal and compositor force-close. X11 additionally checks initial above state
and native resize increments changing from 7x9 to the default. Run under ASan
for the destruction paths. Manual acceptance includes dragging/resizing across
scaled monitors, titlebar controls, activation policy and transient ownership.

Source-only Cppcheck 2.22.0, public API/header inspection and zero-fuzz patch
application are preparation checks. The complete toplevel.cpp translation unit
passes the selected target Clang syntax check with real configured wx and GTK4
headers, including frame style constants without a precompiled header. The
fixture, linking, geometry, WM policy and executable memory-safety acceptance
remain pending the shared GTK4 runtime.

# GTK4 notebook and static-box contract

`patch-gtk4-notebook-statbox` retains native GtkNotebook and GtkFrame widgets.
Notebook selection veto stops the public `switch-page` signal before its
RUN_LAST class handler. Nested selections and structural changes supersede an
older request; weak ownership handles deletion during callbacks. Selected-page
removal sends the changing event before mutation and the changed event after
native and wx page lists agree. Destruction suppresses selection notifications.
Native insertion owns GTK parenting, rather than adding an unmanaged widget
child outside the notebook's GtkStack.

Side-tab labels retain rotation through a small GtkWidget using public measure,
allocation transforms and snapshot APIs. Images retain the shared wx bitmap
bundle provider. Dynamic tab text, padding, size requests and hit testing use
real native widgets and coordinate transforms. Size calculation derives themed
chrome from actual notebook/page requests, without a synthetic GtkWidgetPath.
Static boxes use GtkFrame child APIs, retain label widgets across reparenting,
and measure the actual label and the frame's own CSS border/padding.

Primary references:

- [GtkNotebook selection signal](https://docs.gtk.org/gtk4/signal.Notebook.switch-page.html)
- [GTK4 notebook signal ordering](https://gitlab.gnome.org/GNOME/gtk/-/blob/4.24.1/gtk/gtknotebook.c)
- [GtkWidget allocation transforms](https://docs.gtk.org/gtk4/method.Widget.allocate.html)
- [GtkFrame child and label APIs](https://docs.gtk.org/gtk4/class.Frame.html)

`notebook4-contract` is selected with `BUILD_NOTEBOOK_CONTRACT`. It checks native
selection veto, silent nested selection, deletion of a requested page during
notification, selected-page removal veto, synchronized page removal, dynamic
tab metadata, static-box ownership and notebook destruction during a callback.
Run under ASan for the reentrant destruction paths. Visual acceptance also
covers side-label rotation, bitmap rendering, hit testing, focus navigation and
scaled theme geometry.

The complete notebook.cpp and statbox.cpp translation units, the rotated-label
GtkWidget implementation and notebook4-contract compile with the selected
target Clang, the real configured wx setup.h and GTK4 source/generated headers.
The diagnostic configuration excludes PNG/SVG, GL, WebView and media controls;
these remain separately selected features in the Ports recipe. Linking, GUI
execution and executable memory checking remain pending; syntax checks do not
establish runtime acceptance.

# GTK4 toolbar contract

`patch-gtk4-toolbar` replaces removed GtkToolbar/GtkToolItem APIs with real
GtkButton/GtkToggleButton widgets in a themed GtkBox. Contiguous radio groups
remain owned by wx, including dynamic insertion/removal and OnLeftClick veto.
Split dropdown arrows dispatch wxEVT_TOOL_DROPDOWN and use the common wx popup
menu implementation when unhandled. Tools retain command, hover, right-click,
enabled, checked, label, help, bitmap and embedded-control behavior. Dynamic
conversion between normal and check tools rebuilds its native button; removed
tools can be inserted again. Accessible labels also exist when text is hidden.

Overflow uses a scrolling GtkViewport with scroll-to-focus instead of the
removed GtkToolbar overflow menu. This preserves access to embedded controls,
keyboard focus and all tools in horizontal and vertical layouts. Presentation
and navigation under mouse, keyboard, RTL and touch require GUI acceptance.
Native widget lifetime and copied bitmap providers are independent of tool
objects; callbacks use cleared native lookups and wx weak references when an
event deletes a tool or its toolbar. Generated disabled bitmaps are cached and
invalidated when their source changes. wxAddRemoveCtrl uses the same toolbar.

Primary references:

- [GTK4 button content and activation](https://docs.gtk.org/gtk4/class.Button.html)
- [GtkToggleButton native state](https://docs.gtk.org/gtk4/class.ToggleButton.html)
- [GtkViewport focus scrolling](https://docs.gtk.org/gtk4/method.Viewport.set_scroll_to_focus.html)
- [GTK4 accessible property updates](https://docs.gtk.org/gtk4/method.Accessible.update_property.html)

`toolbar4-contract` is selected with `BUILD_TOOLBAR_CONTRACT`. It activates real
native buttons and checks wx command/state synchronization, check/radio veto,
radio group merging, disabled state, dynamic labels/tooltips/toggle type,
remove/reinsert ownership, dropdown events, text-only to bitmap presentation,
orientation and destruction during a command callback. Run it under ASan for
reentrant lifetime checks. Popup rendering is also covered by menu4-contract;
actual toolbar keyboard delivery, overflow scrolling, icon rendering and focus
notifications remain interactive checks. In particular, claiming a right-click
gesture must remain safe if cancelling a competing gesture delivers a wx
capture-lost handler that deletes the tool or toolbar. A synthetic pressed
signal without a real GDK event sequence does not establish that contract.

The complete toolbar.cpp and common/addremovectrl.cpp translation units and
this fixture pass target Clang syntax checks using real configured wx and GTK4
headers. Source Cppcheck reports no warnings with its GTK/wx libraries. Linking,
GUI execution and executable memory checks remain pending the shared build;
prepared fixtures and successful compilation are not runtime acceptance.

# GTK4 clipboard and shared MIME transport

`patch-gtk4-transfer` uses GdkContentProvider and GdkClipboard. wxDataFormat's
GTK4 native representation is an interned MIME name, matching GdkContentFormats;
GTK2/3 retain their existing GdkAtom representation. No removed selection-data
API or fabricated GDK types are used. One private transport helper snapshots
all supported wx formats into immutable providers and reads native streams
asynchronously through the existing wx event loop. The GTK4 drag-and-drop
consumer uses this same byte transport.

Unicode text is transferred as UTF-8. wxDF_TEXT uses its existing wx locale
encoding at the wx data-object boundary and is converted explicitly to/from
UTF-8 on the native wire. Custom MIME payloads preserve exact lengths, including
zero bytes and empty payloads. Received data has extra terminator storage for
wx file/URI objects without changing the reported payload length. Bitmap data
keeps the shared wx PNG handler. PNG serialization now reports the actual
encoded size instead of exposing spare allocation bytes after IEND.

SetData atomically replaces the offer; AddData forms a union with a locally
owned offer, preferring the new representation for duplicate formats. Clear and
destruction do not erase another provider's contents. Primary selection uses
GDK's separate clipboard and does not overwrite the regular clipboard; Wayland
compositors without the primary-selection protocol can reject that offer.
Flush reports the real asynchronous GDK store result, including an unavailable
clipboard manager, and does not mark a replacement offer as persisted. Pending
reads/stores have cancellable, separately owned callback storage; clipboard
destruction and event-loop shutdown stop waiting without retaining a dangling
wxClipboard pointer. IsSupportedAsync queues the normal wxClipboardEvent.

Primary references:

- [GdkContentProvider and its public virtual methods](https://docs.gtk.org/gdk4/class.ContentProvider.html)
- [Provider union order and ownership](https://docs.gtk.org/gdk4/ctor.ContentProvider.new_union.html)
- [Asynchronous clipboard reads](https://docs.gtk.org/gdk4/method.Clipboard.read_async.html)
- [Remote clipboard persistence](https://docs.gtk.org/gdk4/method.Clipboard.store_async.html)

`clipboard4-contract` (`BUILD_CLIPBOARD_CONTRACT`) checks Unicode interchange
with native GDK, custom binary and empty payloads, AddData/SetData semantics,
format notifications, foreign-owner Clear, primary isolation, PNG round-trip
and exact IEND length. A real GdkContentProvider subclass destroys the requesting
wxClipboard from its asynchronous write callback to exercise request lifetime
under ASan. Run with G_DEBUG=fatal-warnings and a real X11/Wayland display; cross
application paste and clipboard-manager persistence are separate runtime checks.
The test temporarily replaces clipboard contents and clears its test offers.
A real GCancellable signal reenters Requests::Cancel; pending requests are
detached before emission so recursive teardown cannot invalidate iteration.
The regression checks that both requests cancel exactly once; run under ASan
to detect the former invalidated iterator.

Full target syntax checks pass for dataobj.cpp, clipbrd.cpp and the fixture with
real configured wx and GTK4 headers. The diagnostic setup has no PNG handler,
so its conditional PNG fixture section has not been compiled or executed yet.
Source Cppcheck is clean with explicit annotations for GObject initialization
and callbacks that can reenter/delete a clipboard. GUI execution, linking,
PNG acceptance and executable memory checking remain pending the shared build.

# GTK4 drag-and-drop

`patch-gtk4-dnd` uses GtkDropTargetAsync and native GdkDrag on both display
backends. It shares the clipboard provider/stream implementation, preferred MIME
negotiation and text conversion. wx OnEnter/OnDragOver/OnLeave/OnDrop/OnData and
GiveFeedback callbacks retain native drop/drag objects while checking owner
lifetime after application callbacks. Target destruction cancels outstanding
reads; source-window destruction or event-loop shutdown ends synchronous
DoDragDrop through the existing wx event loop. Icons use native drag paintables.
Copy/move/link actions are constrained by the real source offer; wx source flags
retain copy versus default-move policy. No fabricated events, private GDK structs
or second transfer engine are used.

`dnd4-contract` (`BUILD_DND_CONTRACT`) is an interactive executable, deliberately
excluded from automatic CTest. On a real X11 or Wayland display, drag from the
blue source to the green target: check normal copy, Shift move, Ctrl copy and
Escape cancellation. Select the veto mode and verify no successful source result;
select each removal mode to delete the target during OnEnter or after OnData.
Changing modes recreates the target. Close the window during a drag, and drag
UTF-8 text from another application into it. Observe the reported action/counts,
text and application termination, with G_DEBUG=fatal-warnings and ASan enabled.
The fixture reports observations and never prints an automatic acceptance PASS.

Full target syntax checks pass for dnd.cpp, common/dndcmn.cpp and the interactive
fixture using real configured wx/GTK4 headers. Actual drag protocol, callback
ordering, compositor feedback, cross-application interoperability and memory
execution remain pending the shared GTK4/wx build and display runtime.

Primary sources: [GtkDropTargetAsync](https://docs.gtk.org/gtk4/class.DropTargetAsync.html),
[GdkDrag.begin](https://docs.gtk.org/gdk4/ctor.Drag.begin.html),
[GdkDrop.read_async](https://docs.gtk.org/gdk4/method.Drop.read_async.html),
[GdkDrop.finish](https://docs.gtk.org/gdk4/method.Drop.finish.html).

# GTK4 native DataView

`patch-gtk4-dataview` retains GtkTreeView and its wx model/sort/selection bridge.
GTK4.24 still provides these public APIs, deprecated since 4.10. Custom cells
measure through GtkCellRenderer preferred-size methods and render through real
GtkSnapshot Cairo nodes. Custom RenderText snapshots the native text renderer;
bitmap bundles keep logical dimensions and select assets for the widget scale.
Custom editors use a GtkBox implementing GtkCellEditable and store its actual
editing-canceled property. Header and context-menu input uses event controllers
and real event/widget coordinate transforms.

Tree drag sources return the shared immutable MIME provider. Tree destinations
use wxDropTarget and the same asynchronous byte reader as clipboard and ordinary
DnD; all enabled MIME formats are offered to negotiation. DROP_POSSIBLE retains
its data-format/size contract, DROP receives owned event bytes, and wx vetoes
control acceptance. Native row highlighting, timed hover expansion and edge
scrolling use public GtkTreeView/GtkScrollable APIs. Pending reads, timer callbacks
and nested events retain separate state; weak owner checks and motion generations
prevent stale callbacks from accessing a removed view or repainting an old drop.
The existing native tree-source policy remains copy-only.

`dataview4-contract` (`BUILD_DATAVIEW_CONTRACT`) exercises native selection, text
edit and toggle signals, custom cell measurement and snapshot rendering, native
editor cancellation state, sorting and model removal. Run the same executable
with positional argument `interactive` for native tree-row drag/drop, veto,
hover expansion, edge scrolling, external text drops, target replacement and
destruction during DROP_POSSIBLE. This interactive mode reports observations; it does not print an
automatic acceptance result. Use a real X11 or Wayland display, fatal GTK warnings
and an instrumented build for callback lifetime checks.

The complete target dataview.cpp translation unit and both fixture modes pass
syntax checking against configured wx/GTK4 headers. Native display execution,
rendered pixels, actual editor interaction, drag protocol and ASan acceptance
remain pending the shared build. No generic DataView replacement or fake GTK
selection structures are introduced.

Primary sources: [GtkTreeView](https://docs.gtk.org/gtk4/class.TreeView.html),
[GtkCellRenderer.snapshot](https://docs.gtk.org/gtk4/vfunc.CellRenderer.snapshot.html),
[GtkCellEditable](https://docs.gtk.org/gtk4/iface.CellEditable.html),
[GtkTreeDragSource](https://docs.gtk.org/gtk4/iface.TreeDragSource.html).

# GTK4 cursor bitmaps, native widgets and MDI

The GTK4 cursor-to-bitmap constructor copies pixels from the cursor's borrowed
`GdkTexture` into an owned pixbuf. Named cursors do not expose a texture in GTK4;
converting one, or an invalid cursor, yields an invalid bitmap. It does not
substitute a theme image. Display lookup uses the GTK4 X11 header and a helper
name distinct from `wxDisplayFactory::GetDisplay(unsigned)`.

MDI child menus use the parent GtkBox and GTK4 measurement, retaining their
position above the notebook and their non-expanding vertical layout. MIME icon
lookup uses the display's GtkIconTheme and releases both the icon paintable and
its returned GFile. The filename interface returns a local path when available;
resource-backed and generated icons have no local filename and return empty.
GTK4 can return SVG icon files; loading remains the responsibility of the
existing image/icon consumer. GTK3 keeps its original lookup flags and API.

`native-small4-contract` checks custom cursor RGBA pixels after cursor disposal,
the named/invalid cursor boundary, native widget retention and explicit ownership
transfer, and MDI menu parenting/client geometry. Build it with
`BUILD_NATIVE_SMALL_CONTRACT=ON` using the same SDK/installed wx-config as the
other GUI contracts. It requires a display and returns failures through OnRun.
Target syntax and Clang Static Analyzer checks cover the modified translation
units; linked execution, GUI behavior and runtime memory checks remain pending.

GTK4 continues to define `wxHAS_NATIVE_WINDOW`: unparented GtkWidgets can be
embedded, retained by their caller after wrapper deletion, or transferred with
`Disown()`. Both floating and already-owned native widget references are covered.
GTK4 does not define `wxHAS_NATIVE_CONTAINER_WINDOW`: it has no public equivalent
of GTK3's foreign GdkWindow ownership/reparent API. This capability boundary is
checked by the fixture at compile time; foreign toplevel embedding is not
represented by a successful no-op Create. GTK3's existing container path is
unchanged.

# GTK4 bitmap overlays

`patch-gtk4-overlay` selects the existing common bitmap overlay on GTK4.
It captures and restores pixels through the shared Cairo drawing context and
the retained wxPizza client content. GTK3 retains its existing Wayland popup
implementation. There is no second overlay engine or removed drawing feature.
The client content path requires an already painted wx window; it does not
capture other windows, desktop pixels or native child controls.

`overlay4-contract` checks capture, clipping, clear and reset on memory drawing
contexts at scales 1 and 2, then on a painted window's ClientDC. A fresh ClientDC
must see the restored content after the first drawing session ends. Build it
with `BUILD_OVERLAY_CONTRACT=ON`; run on a real GTK4 display, including a scaled
display for window HiDPI acceptance. The modified overlay translation units and
fixture pass target syntax checks. Linked GUI execution and pixel checks remain
pending the shared wxGTK4 build.

# GTK4 window shapes on X11

`patch-gtk4-shape` keeps region and path shapes using the X11 Shape extension.
It sets the server's visual Bounding shape and GTK's input region, including
native widget/surface offsets and device scaling. GTK's native render and input
translations in `gtk/gtknative.c` and `gtk/gtkwindow.c` define the coordinate
mapping. This is visual clipping, not an input-only approximation. Path masks
and their painted border retain the existing wxGraphicsPath implementation.

The shape object survives realization and remains available for Clear,
re-realization, allocation and scale changes. X11 Shape protocol coordinate
limits are checked before requests. GTK4/Wayland has no public visual-shape API;
SetShape returns false there even before the widget is realized. No second
window or GTK renderer is introduced. GTK3 retains its existing backend.

GTK4 X11 configuration requires the common libXi and libXext providers in both
autoconf and CMake. Run the focused dependency regression with selected host
tools:

```sh
python3 tests/x11-shape-selection.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --work-parent /work/tmp
```

It executes the actual configure selection block and checks the complete X11
set, missing Shape/input providers, Wayland-only GTK4 and unchanged GTK3. The
unmodified selection fails the missing-Shape case by accepting absent libXext.

Build `shape4-contract` with `BUILD_SHAPE_CONTRACT=ON` against installed wxGTK4.
Its X11 CTest cases require a real X server, run with GDK_SCALE=1 and 2, and
verify the actual surface scale and server-side Bounding/Input rectangles for
interior, hole and exterior pixels. They cover pre-realize selection, Clear,
post-realize replacement, surface re-realization, path shapes and final reset.
Running the executable with a Wayland backend instead verifies explicit shape
refusal. Target TU/fixture syntax and Clang Static Analyzer checks pass; the
five-case dependency regression passes. Linked GUI execution, WM behavior and
runtime memory checks remain pending and are not implied by these checks.

# GTK4 popup windows

`patch-gtk4-popup` implements ordinary and transient wx popup windows with
GtkPopover and a real GdkPopup surface. The nearest wxPizza ancestor owns the
native popup. A null wx parent uses the application's existing top window;
creation fails explicitly if no suitable owner exists. Showing requires that
owner to be mapped. No hidden owner window is created.

Ordinary popups do not grab input. Transient popups use GTK's native autohide
and input handling; the GTK3 GdkWindow/seat-grab path is not compiled on GTK4.
Native dismissal flows into the common wx focus/dismiss handlers. Explicit
Dismiss does not call OnDismiss, and weak references protect continuation after
application callbacks destroy a popup. Positioning reuses the shared surface
coordinate helpers and compositor constraints. X11 coordinates are global;
Wayland coordinates remain relative to the owning toplevel. Mapped GetPosition
reports the actual popup surface position after compositor adjustments.

`popup4-contract` covers native parent surfaces, null-parent ownership, ordinary
versus transient grabs, child controls, dismissal/reopening, and destruction
from show/hide callbacks. Build it with `BUILD_POPUP_CONTRACT=ON`, then run with
a real GTK4 display and `G_DEBUG=fatal-warnings`. Both modified translation
units pass target syntax and Clang Static Analyzer checks; the fixture passes
target syntax checking. Linked execution, real outside-click/Escape delivery,
focus interaction, multi-monitor/HiDPI positioning and runtime memory checks
remain pending the shared wxGTK4 build.

Primary references: [GtkPopover](https://docs.gtk.org/gtk4/class.Popover.html),
[GTK4 migration](https://docs.gtk.org/gtk4/migrating-3to4.html).

# Cross pkg-config sysroot selection

`pkgconfig-sysroot.py` executes wx configure's cross-root block with the
selected real pkg-config executable and conflicting host/target `.pc` files.
It checks native selection, preservation of an explicit `PKG_CONFIG_PATH`,
legacy linker-root fallback without a declared sysroot, and target metadata
selection when a cross SDK declares `PKG_CONFIG_SYSROOT_DIR` but leaves
`PKG_CONFIG_PATH` empty. The latter catches host linker paths shadowing target
pkg-config metadata.

```sh
python3 tests/pkgconfig-sysroot.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

# Common Scintilla/Lexilla provider contract

The wx 3.2 public STC interface is retained while its frontend consumes the
common `devel/scintilla-core` and `devel/lexilla` packages. Scintilla 5.6.9 is a
PIC toolkit-neutral core archive; wx supplies the window, font, surface and
completion-list implementations. Lexilla 5.5.5 supplies the shared lexer
catalogue and its common PIC loadable-lexer access helper. Both Autoconf and
CMake require these installed providers; embedded Scintilla/lexer source is
not compiled or linked. The private core headers and archive must have the
same version and compiler/runtime ABI.

The public numeric/name lexer methods select current ILexer5 instances. Plugin
loading uses upstream LexillaAccess; plugins must implement the current Lexilla
interface. Modern style bytes always have eight bits, independently of
indicators; the retained `SetStyleBits` method therefore has no effect and both
style-bit queries return eight. Generated wx 3.2 public methods are maintained
as part of this adapter; automatic regeneration from a newer Scintilla protocol
is disabled because it would remove existing wx public APIs.

```sh
python3 tests/scintilla-selection.py --source /prepared/wxWidgets \
  --shell /native/bin/mksh --pkg-config /native/bin/pkg-config \
  --work-parent /work/tmp
```

This runs the actual generated-configure provider selection with real pkg-config
metadata. Native and target sysroot cases, either missing provider and explicitly
disabled STC are distinct cases. The ordinary static wx-config link path carries
the provider libraries through `WXCONFIG_LIBS_STC`, while full sysroot search
paths remain in build-only `EXTRALIBS_STC`. Installed `wx-config --prefix`
resolves the common providers in the selected prefix. Static/shared and
monolithic variants are covered. Base-only consumers do not gain editor link
dependencies. A shared wx consumer links the wx STC DSO.

The optional CMake static export discovers ScintillaCore and Lexilla with
`find_dependency`; shared and STC-disabled exports do not require their
development targets. This config-consumer fixture uses the real package
config template and imported-target fixtures, without compiling libraries:

```sh
python3 tests/stc-cmake-config.py --cmake /native/bin/cmake \
  --template /prepared/wxWidgets/build/cmake/wxWidgetsConfig.cmake.in \
  --work /work/tmp/wx-cmake-config
```

The `stc4-contract` GUI target checks UTF-8 offsets/undo, numeric and named lexer
selection, real Python keyword styling, completion notification data, calltips
and repeated popup creation/destruction. Run it on the matching GTK4 target with
a real display; the CTest timeout is 20 seconds. It does not establish shaped
bidirectional text, external plugin compatibility, interactive IME, printing or
complete KiCad acceptance. Memory-instrumented execution is a separate run.

The three adapted frontend translation units and the GUI fixture pass target
Clang syntax checking against the new provider headers. Clang Static Analyzer
and Cppcheck 2.22 completed for the bridge; successful tool execution does not
mean there were no diagnostics. CSA reported six pre-existing buffer paths
whose realloc branch is unreachable with the getters' allocated `len+1`
capacity. Cppcheck reported wx hash-map macro, union-storage reference and
trait-selected movable-vector diagnostics, plus existing API/style warnings;
review established no new actionable bridge defect. The old wx 3.2 bridge
cannot serve as a compiling baseline against GTK4 headers. These checks do not
replace runtime memory checks. Full wx package acceptance and execution of the
GUI fixture remain pending.
