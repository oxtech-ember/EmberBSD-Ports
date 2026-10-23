# gspell current C library and build tools

This recipe uses gspell 1.14.5. The stable release date is 2026-09-26.
The source archive and the imported recipe follow GNOME and NetBSD pkgsrc.
The import preserves the NetBSD recipe notices and the upstream LGPL license.
The public API floor stays at 1.0.1. The package ABI floor is 1.14.5 for
native and cross builds. The upstream shared library keeps SONAME 3.

Upstream builds C sources. It does not compile Vala sources or link libvala.
It generates GObject Introspection data from the target C library. It then
runs `vapigen` on that GIR to install `gspell-1.vapi` and `gspell-1.deps`.
The VAPI input package is `gtk+-3.0`.

`TOOL_DEPENDS` selects the native Vala package. That package provides the
native `vapigen-0.56` program and the portable VAPI data for GTK and GLib.
`MESON_BINARY.vapigen` binds that program through the existing Meson machine
file API. No target Vala compiler or libvala buildlink is needed.
The Vala provider retains its own options, tests and runtime requirements.

Cross builds use the common GObject Introspection `cross.mk` contract.
Use an export with the common graphics infrastructure. The native scanner
and compiler retain real target GType queries. gspell has no GI-specific
Meson options, so it shares the tools without adding those provider options.
The target GI package supplies build metadata. It is not a runtime library
dependency of the gspell C library. The C dependencies remain Gio, GTK3,
Enchant and ICU, with their normal transitive libraries.

The recipe retains `gtk_doc=false` and `install_tests=false` from pkgsrc.
It keeps the upstream enabled defaults for GIR, VAPI, the application and
building the tests. No test, GIR or VAPI feature is disabled for cross builds.

Source review does not establish package, target runtime or memory acceptance.
Fresh native tool and target library predicates, the generated GIR and VAPI,
normal package payloads and target execution remain separate checks.
