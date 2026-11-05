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
static GLib build. Unsupported, static and explicitly absolute layouts retain
the configured locale fallback. The corresponding configured path may remain
in a binary: permit that specific prefix during package qualification only
after verifying the exact relocated artifact and its loaded library.
