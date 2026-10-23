# libnotify

This common recipe selects [libnotify 0.8.9](https://download.gnome.org/sources/libnotify/0.8/).
The official release archive SHA256 is
`c906bb084027ea512f94a60fbfc0cc8d4f17e4b4d525bed370d07a6d8714c923`.
The recipe retains NetBSD pkgsrc attribution, platform rules and the LGPL license.
It applies no C implementation patch. The API floor remains 0.7.0.
The package ABI floor is 0.8.9 for native and cross consumers.
The release retains SONAME `libnotify.so.4` and the Notify-0.7 GIR namespace.
GLib 2.62 or later is required.

The default man-page build uses DocBook 5 input with the
`http://docbook.org/ns/docbook` namespace. Its native `docbook-xsl-ns`
tool dependency requires `docbook-xsl-ns>=1.79.2nb1` for the matching
namespaced stylesheets and corrected XML catalog. The `xsltproc --nonet` stylesheet lookup must succeed locally.
This dependency is separate from the optional `doc` selection.

The optional `doc` and `tests` selections remain disabled by default.
Native builds retain GIR. Cross builds retain the existing C API and
`notify-send` payload without GIR. Native API documents require GIR;
the selected DocBook specification remains available in either mode.
Cross GIR restoration remains separate work.

The `tests` option needs target GTK4 build headers and native D-Bus tools,
Python, `dbus` and `dbusmock`. Configuration refuses missing native prerequisites.
A `dbusmock` package provider is not available in the current pkgsrc tree.
Do not accept upstream's empty test list as a successful C test suite.
The source declares 20 C test programs and one Python CLI test.
Native tests use a private mock session bus. Graphical and interactive suites
have additional display requirements. Cross test execution needs a target plan.
Package, target notifications, display and memory acceptance remain separate.
