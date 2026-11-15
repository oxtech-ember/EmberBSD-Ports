# XApp application library

This package builds Linux Mint XApp 3.4.0 at upstream tag `3.4.0`
(commit `150a1d5f556c`), with `app-lib-only=true` and GObject
Introspection enabled. It supplies `libxapp`, `XApp-1.0.typelib`, the
PyGObject override, public core headers, schema and translations. The
consumer Web App Manager uses `XApp.IconChooserButton` and the GTK3 API.
The XApp core retains its own status icon API, without the desktop watcher.

The GTK provider must provide X11 and introspection; the X11 backend is built
unconditionally by upstream. The private xapp-shell Wayland backend is enabled
exactly when the chosen GTK provider has Wayland, with the common native
Wayland scanner for cross builds. The backend requires compositor support for
xapp-shell; it is not a claim that every Wayland compositor provides it.
GTK layer shell is disabled. Mint scripts, desktop panel applets, notifier
watcher, GTK module and the keyboard layout controller are excluded. In
particular `XAppKbdLayoutController` is absent from this API and typelib.

The explicit Wayland feature patch is local to EmberBSD and was prepared
with AI assistance; it makes Meson fail if the selected backend cannot find
its declared inputs rather than silently changing the package capability.
The upstream license is LGPL-3.0 (see `COPYING.LESSER`).

Cross-GI uses `devel/gobject-introspection/cross.mk`. The amd64 dump under
`files/gi-dump` was captured from an EmberBSD amd64 target during GIR generation. Its replay with
the scanner's actual type list remains to be verified. Staged install, GI
runtime import and target behavior remain separate acceptance checks.
