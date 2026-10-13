# Configtool cross-build paths

Fcitx Configtool 5.1.16nb1 separates configure-time discovery from target data paths.
The original `FindIsoCodes.cmake` finds host-readable files in the target sysroot.
The original `FindXKeyboardConfig.cmake` obtains paths from pkg-config.
Both modules remain unchanged.

The new `*_RUNTIME` cache entries default to the discovered paths for native builds.
The Ports recipe supplies installed paths from each dependency's `BUILDLINK_PREFIX`.
It falls back to `PREFIX` when buildlink has not set that value.
It does not add `_CROSS_DESTDIR` to runtime paths.
The three ISO639 JSON files and the XKB base enter `config.h` through these entries.
`XKEYBOARDCONFIG_DATADIR` remains a discovery value; Configtool does not use it at runtime.
The existing C/C++ macro names, features and data formats remain unchanged.

The compiler-settings include uses `Fcitx5Utils_DIR`, which `find_package` resolves on the build host.
`FCITX_INSTALL_CMAKECONFIG_DIR` retains its target installation meaning.
The recipe selects native `msgfmt` and `msgmerge` through pkgsrc's tool paths.
It retains Qt6, the KDE configuration module, X11 dependencies and both configuration interfaces.

## Regression

Use an exported toolkit pkgsrc tree and the normal cross-build MAKECONF.
Set the native tool paths. The output directory must not exist.
No package is built, installed or registered by this test.

```sh
BMAKE=/absolute/native/bmake CMAKE=/absolute/native/cmake \
    sh tests/runtime-data-paths.sh \
    /absolute/exported-pkgsrc \
    /absolute/cross-mk.conf \
    /absolute/fcitx5-configtool-5.1.16.tar.zst \
    /absolute/new-results
```

The runner verifies the pinned archive SHA256 and all patch SHA1 values.
It extracts the real upstream source and applies the patches with zero fuzz.
CMake uses the actual `FindIsoCodes.cmake`, `FindXKeyboardConfig.cmake` and `config.h.in`.
Controlled `.pc`, JSON and XKB files isolate discovery from unrelated host packages.
The test covers these cases:

- Original and patched native builds keep native defaults.
- Original cross configuration exposes a sysroot path in `config.h`.
- Patched cross configuration emits `/usr/pkg` paths and preserves discovery values.
- A separate `/opt/ember-test` prefix passes the same checks.
- Missing ISO639-3 data fails the real required `FindIsoCodes` check.
- The exact compiler-module include fails with the original target path and resolves after the patch.
- Native and cross recipe metadata select both native Gettext tools and the target data paths.
- Separate dependency-prefix overrides survive recipe expansion.

Runtime overrides are passed as CMake `-D` cache arguments, as in the package build.
Expected header paths are independent constants, not values read back from the runtime cache.
The compiler-include case uses a marker module to test resolution; it does not test the compiler settings themselves.

The configuration regression passed with CMake 4.4.4 and pkgconf 3.0.8 on macOS.
It does not configure or compile the complete Qt/KF application.
It does not prove language-list parsing, keyboard previews, an input session or target runtime behavior.
Normal package checks and the configuration interfaces must still run on EmberBSD.
Upstream defines no executable test target for this release.

These patches change CMake configuration and string substitutions, not C/C++ logic.
Cppcheck, path analysis and Valgrind were not rerun for this configuration-only change.
No source-analysis or memory-safety pass is claimed by this regression.
The patch series and regression are AI-assisted EmberBSD changes. They have not been accepted upstream.
