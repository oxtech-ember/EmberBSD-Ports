# Pango shared recipe

Pango 1.58.2 is the current stable release in the
[GNOME source index](https://download.gnome.org/sources/pango/1.58/).
The separately listed [1.90 release](https://download.gnome.org/sources/pango/1.90/pango-1.90.0.news)
is an experimental, ABI-incompatible Pango 2 development release.

The exported, deprecated `pango_get_sysconf_subdirectory()` and
`pango_get_lib_subdirectory()` ABI still returns directory paths, even though
Pango no longer uses these getters internally. The common patch relocates their
prefix-owned defaults relative to the loaded `libpango-1.0` on Darwin, NetBSD
and Linux when Meson verifies `dladdr`. It uses a private data anchor and the
configured library-directory suffix, following the common GLib path approach.
The complete prefix layout must be preserved when moving a package.

`PANGO_SYSCONFDIR` and `PANGO_LIBDIR`, including explicit empty values, retain
precedence. Results remain cached once per getter and owned by Pango. Explicit
paths outside the configured prefix, static executables, unsupported platforms
and unrecognized library layouts retain the upstream configured defaults.
Missing relocated directories do not cause a lookup in the producer prefix.
No new public API or environment requirement is introduced.

Run the focused native check using the selected SDK Python and built library:

```sh
"$HOST_PREFIX/bin/python3.15" tests/relative-directories.py \
    "$HOST_PREFIX/lib/libpango-1.0.0.dylib"
```

Use the corresponding `.so` library on ELF hosts. The fixture only copies that
library into a temporary prefix, calls both exported getters, and checks
defaults, environment overrides and stable cached pointers. Its dependencies
may still load from the original prefix; full SDK relocation qualification is
separate. Native Darwin ARM64 1.58.2nb4 compilation, packaging, installation
and this fixture pass with Clang 23.1.4. The same fixture passes with the changed
`pango-utils.c` instrumented by ASan/UBSan and linked with retained ordinary
library objects; other units and dependencies were not instrumented. Darwin
ARM64 is outside the [Valgrind platform list](https://valgrind.org/info/platforms.html).
Cppcheck 2.22.0 reproduces the same GLib-header warning in the original and
changed unit; Clang Static Analyzer 23.1.4 reports no finding in either. Both use
the real native buildlink flags. Static consumers, the full signed-package
lifecycle and target execution remain separate checks.
