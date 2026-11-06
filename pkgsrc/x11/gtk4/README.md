# GTK4 shared toolkit

This recipe owns GTK 4.24.1 and its target dependencies for all Ports consumers.
Backend selection follows the target OPSYS, so a Darwin host can build X11 and
Wayland for EmberBSD without selecting the host Quartz backend.

Wayland protocol button codes come from the shared `devel/input-headers`
provider. Introspection uses `devel/gobject-introspection/cross.mk`: the selected
host scanner is wrapped with target ELF dependency inspection and the existing
target GType query/replay mechanism. The GTK recipe does not maintain a second
scanner, input-header copy, or private compiler stack.

The official archive checksums, cross configure, selected host Wayland
scanner and target C compilation have been exercised. The full package,
introspection output, installation manifest and GUI runtime are still being
validated; source preparation is not a published GTK4 binary.
