# GTK4 shared toolkit

This recipe owns GTK 4.24.1 and its target dependencies for all Ports consumers.
Backend selection follows the target OPSYS, so a Darwin host can build X11 and
Wayland for EmberBSD without selecting the host Quartz backend.

Wayland protocol button codes come from the shared `devel/input-headers`
provider. Introspection uses `devel/gobject-introspection/cross.mk`: the selected
host scanner is wrapped with target ELF dependency inspection and the existing
target GType query/replay mechanism. The GTK recipe does not maintain a second
scanner, input-header copy, or private compiler stack.

The `tests` package option explicitly enables Meson's `build-tests` and
`build-testsuite`. They are disabled for ordinary toolkit builds. With tests
enabled, `colorstate` links the existing `udmabuf.c` helper on every platform:
plain texture/PNG checks remain available, and DMA-BUF cases use upstream's
unsupported-operation result when the backend is absent. DRM format headers
alone do not establish DMA-BUF support.

The official archive checksums, cross configure, selected host Wayland
scanner and target C compilation have been exercised. The full package,
introspection output, installation manifest and GUI runtime are still being
validated; source preparation is not a published GTK4 binary.

The embedded `GtkFileChooserWidget` and `GtkFileChooserDialog` expose two
EmberBSD instance properties: `show-hidden` and `do-overwrite-confirmation`.
An explicitly set hidden-file value survives remapping and does not overwrite
the desktop hidden-file preference. Overwrite confirmation defaults to true,
preserving GTK4 behavior; applications implementing their own save policy can
turn it off. These properties are not advertised on `GtkFileChooserNative`,
the `GtkFileChooser` interface, or portal implementations.

The two concrete classes also expose `selection-changed`,
`current-folder-changed`, and `file-activated` signals. Selection changes are
coalesced on the default main context after internal model/entry transitions;
callbacks query the current selection with the public GFile APIs. Disposal
cancels pending delivery. Folder notifications follow successful asynchronous
navigation; activation occurs before native acceptance. These capabilities
serve embedded file controls and native dialogs without exposing private
chooser state. The wxGTK32 file-chooser fixture exercises the shared contract.
Both modified GTK translation units pass target syntax compilation. Real
chooser execution, including desktop preference isolation, remains pending.
