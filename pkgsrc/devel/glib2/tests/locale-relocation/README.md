# GLib locale relocation tests

These explicit diagnostic tests do not run during package builds. Use the
selected native SDK tools and absolute paths for the inputs and output.

`relocated-locale.py --cc CC --msgfmt MSGFMT --sdk PREFIX --old-lib OLD_DYLIB
--new-lib NEW_DYLIB --old-tool OLD_GSETTINGS --new-tool NEW_GSETTINGS
--output WORKDIR` tests the loaded DSO and gsettings against a synthetic French
catalog, with the original prefix still present. It requires a working
`fr_FR.UTF-8` locale (or pass `--locale`). This runner currently targets Darwin.
Use the library and executable extracted from the exact package to qualify it.

`locale-fallback.py --source PATCHED_SOURCE --cc CC --sdk PREFIX --output
WORKDIR` exercises the actual resolver with relocation unavailable and with a
static executable anchor. This covers those resolver branches, not a complete
static GLib build. Unsupported and static layouts, and paths outside the configured prefix, retain
the configured locale fallback. The corresponding configured path may remain
in a binary: permit that specific prefix during package qualification only
after classifying all remaining references and verifying the exact relocated
artifact and its loaded library.

`owned-paths.py --cc CC --sdk PREFIX --old-glib OLD_DYLIB --new-glib
NEW_DYLIB --new-gio NEW_GIO_DYLIB --new-girepository NEW_GI_DYLIB
--update-mime-database TOOL --output WORKDIR` tests loaded-library
identity, relocated XDG defaults, locale aliases and the GIO launcher, plus
environment overrides, external paths, layout mismatch and static anchor. It
also checks GIO module discovery and GIRepository typelibs in the relocated
layout; the latter requires the native SDK GLib, GLibUnix, GObject and Gio
typelib files.
This runner targets Darwin and requires `en_US.UTF-8`; it keeps the original
prefix available while exercising synthetic relocated inputs.

`mime-regression.py --cc CC --sdk PREFIX --update-mime-database TOOL
--new-glib NEW_GLIB --new-gio NEW_GIO --old-glib OLD_GLIB --old-gio OLD_GIO
--output WORKDIR` checks old first-lookup failure, new default lookup,
explicit setter before and after lookup, and concurrent queries and setter
against two synthetic MIME databases. The timeout detects hangs. Darwin only.
