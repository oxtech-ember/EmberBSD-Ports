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
It uses the existing GTK4 native IM controllers, GtkText's native edit batching,
and GtkTextBuffer user-action signals. Clipboard signals/actions operate on the
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
