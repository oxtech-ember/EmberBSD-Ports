# Soup 3 introspection during cross builds

The shared libsoup 3.8.0 recipe retains `Soup-3.0.gir` and
`Soup-3.0.typelib` for native and cross packages. Native GI tools inspect the
target library through the [common GI query contract](introspection.md).
The cross package requires target GLib metadata. Its scanner reads the target
GIR directory, and the temporary query uses the in-tree target Soup DSO.
The native build keeps its upstream generator selection.

The [source patch](libsoup3-gir-cross.patch) changes only Meson generation.
It is an EmberBSD AI-assisted adaptation of the existing Pango and libsecret
cross pattern. It is not submitted upstream. The source owner remains
[GNOME libsoup 3.8.0](https://download.gnome.org/sources/libsoup/3.8/libsoup-3.8.0.tar.xz).
The inherited pkgsrc recipe and upstream LGPL notices remain unchanged.
The release adds Zstandard decoding and compression dictionary request headers.
The recipe declares Zstandard and the upstream GLib 2.70 minimum.

The native and cross recipes explicitly set `docs=disabled`. The pinned pkgsrc
package does not list the optional API HTML, declares no gi-docgen tool and
supports only the `gssapi` package option. Upstream `docs=auto` would install the
HTML merely because native gi-docgen is available for another package. The
explicit value preserves this package-content contract. It does not disable
the library API, GIR, typelibs or upstream runtime tests.

The cross recipe retains its existing `tests=false` and `tls_check=false`.
Upstream `tls_check` executes a configure program that checks the selected GIO
TLS backend. Its option description permits packaging without this probe when
`glib-networking` is a runtime dependency. This recipe retains that dependency.
Neither setting establishes TLS runtime acceptance or a passing upstream suite.
This change does not widen either setting or disable GObject introspection.

The [focused check](../tests/libsoup-gi.py) evaluates the actual release-derived
`gnome.generate_gir()` block with real Meson and GI providers. Supply the same
native and cross machine files as the configured recipe, an explicit SDK source,
and new private output. Repeat `--lock-root` for each shared lock namespace and
`--read-root` for each immutable provider. It checks native/cross scanner and
compiler commands without building or executing Soup. Normal packaging,
real target GType queries, installed import and TLS tests are separate gates.

The docs-auto regression requires native gi-docgen; this test prerequisite does not add a package tool dependency.
