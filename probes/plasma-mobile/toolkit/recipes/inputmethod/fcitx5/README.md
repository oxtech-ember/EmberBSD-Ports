# Fcitx5 input framework

These recipes select the official September 23, 2026 releases:
Fcitx5 5.1.23, Fcitx5 Qt 5.1.16 and Configtool 5.1.16.
The latter two use the common Qt 6.12 and Frameworks 6.31 providers.
Configtool retains its KDE control module and standalone configuration UI.
The core retains Wayland, X11, Enchant, keyboard, emoji, spell and tests.
The Qt adapter retains its Wayland integration.

Core 5.1.23nb4 has a complete cross package and 445 checked files on CM5.
The corrected core PLIST matches its staged payload. Qt and Configtool still
require complete package acceptance. The full Plasma input session remains
unaccepted. Scoped source analysis and native memory checks are described below;
no target memory-analysis pass is claimed.
This Configtool release contains no test targets. Its input and UI integration
requires separate acceptance; no unused test-enable option is passed.

## Sources

The archives come from the [official release server](https://download.fcitx-im.org/fcitx5/).
The following hashes are local SHA256 records. They are not signature verification.

| Archive | SHA256 |
| --- | --- |
| `fcitx5-5.1.23.tar.zst` | `d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b` |
| `fcitx5-qt-5.1.16.tar.zst` | `2d49cb4dfade430e822377beabae5f23da5caf2b2ff49e1eb54213b64dd0840e` |
| `fcitx5-configtool-5.1.16.tar.zst` | `0d9b9e023d3aa7056ec185ed9e6ccfb94e5a5b930d3dd742dba7f37a49abd61e` |
| `en_dict-20121020.tar.gz` | `c44a5d7847925eea9e4d2d04748d442cd28dd9299a0b572ef7d91eac4f5a6ceb` |

The spell data version is still selected by current upstream source.
Its hash matches the upstream CMake download contract. It is vocabulary data,
not an older compiler or parallel runtime. The release contains emoji data;
the obsolete CLDR 37 build dependency is removed.

The recipes derive from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
Retain its RCS identifiers, maintainers and licenses. The SunOS endian/dlmopen
and BSD UUID header adaptations remain. The GCC 7 patches are unnecessary
with GCC 16. The obsolete fmt patch removed log timestamps; current Fcitx5 uses
C++20 logging and no longer needs that patch. The old configtool linker patch
is not carried into Qt6/KF6. Its former runtime-path failure must be checked
against the complete new package.

The cross dictionary and Qt plugin path patches are AI-assisted EmberBSD work.
They have not been accepted upstream. All patches apply without fuzz to the
recorded archives. The target spell compiler remains built and installed.

## Cross requirements and validation

Set `EMBERBSD_FCITX5_COMP_SPELL_DICT` to a native executable built from Fcitx5
5.1.23. Build it with [the native helper](../../../cross/build-fcitx5-host.sh).
The helper verifies both input archives and exact dictionary output bytes.
Pass the distfiles directory, native dependency prefix, ECM CMake directory
and a new work directory. Set absolute CMAKE, NINJA, HOST_CC and HOST_CXX paths.
The named host generator does not need desktop backends; the target retains them.
A Mac run passes all 122905 entries, malformed inputs and an ASan/UBSan repeat.
Clang analysis retains one inherited unconfirmed StandardPath warning.
Cppcheck cannot parse the actual Apple SDK headers; its coverage remains incomplete.
Neither Valgrind nor a leak-checking pass is claimed.
Set `EMBERBSD_WAYLAND_SCANNER` to the common native Wayland scanner.
Use the existing Qt and KF6 host-tool paths from the toolkit workflow.
The Qt plugin receives the target `/usr/pkg/qt6/plugins` installation path;
a host qmake must not select the target installation directory.

`msgfmt` and `msgmerge` are declared as build tools. CMake receives their
pkgsrc-selected host paths. The target `gettext-lib` and `gettext-tools`
dependencies remain: the core uses LibIntl, while the diagnostic and
configuration shell scripts use the `gettext` command. The common
gettext-tools cross recipe retains target `xz` for `autopoint`; a separate
host `xz` compresses its infrastructure archive during the build.

The focused check evaluates native and cross metadata. It then runs the
upstream translation macros with the selected host tools. All 14 release
catalogs, desktop translations and AppStream XML translations pass on Mac.
This check builds no Fcitx C/C++ code and executes no target programs.

```sh
BMAKE=/absolute/native/bmake CMAKE=/absolute/native/cmake \
    sh tests/gettext-tools.sh /absolute/exported-pkgsrc \
    /absolute/cross-mk.conf /absolute/fcitx5-recipe \
    /absolute/fcitx5-5.1.23 /absolute/new-results
```

The LibIntl include path follows the selected gettext provider. Built-in
headers use the provider prefix, with the cross sysroot where applicable.
Package headers use buildlink's `include/gettext` to `include` mapping.
The selection runs after `gettext-lib/buildlink3.mk` reads `builtin.mk`.
The UUID include path is unchanged.

The header regression evaluates actual metadata after `_PKGSRC_BARRIER`.
Earlier metadata queries can show prefixes that are not initialized yet.
It runs the real `buildlink-gettext` target in private work directories.
It then configures the upstream `FindLibIntl.cmake` and compiles an object
through its imported target. It requires installed native and target gettext
packages and target base headers. It never installs dependencies.

```sh
BMAKE=/absolute/native/bmake CMAKE=/absolute/native/cmake \
    NINJA=/absolute/native/ninja NATIVE_CC=/absolute/native/clang \
    NATIVE_AR=/absolute/native/llvm-ar CROSS_CC=/absolute/cross/gcc \
    sh tests/libintl-headers.sh /absolute/exported-pkgsrc \
    /absolute/cross-mk.conf /absolute/fcitx5-recipe \
    /absolute/fcitx5-5.1.23 /absolute/new-results
```

Cross/base, cross/package and native/package cases pass on Mac with GCC16
and Clang23. The previous recipe fails the cross/package imported-header
check. These checks do not build Fcitx5, link a complete consumer, execute
target code, or establish input-session acceptance.

Enchant and XCB IMdkit must be available in the current sysroot before the full
build. Fcitx5 itself does not require GTK. Configtool's Frameworks chain must
use the core libcanberra provider without its optional GTK adapters.
Changing input frameworks alone does not remove that transitive dependency.

Run the recipe metadata check after exporting these recipes:

```sh
BMAKE=/absolute/native/bmake sh ../../../tests/fcitx5-providers.sh \
    /absolute/exported-pkgsrc /absolute/cross-mk.conf \
    /absolute/verified-distfiles /absolute/new-results
```

The check verifies source and patch hashes, then evaluates real native and cross metadata. It rejects Qt5 and GTK
in the selected dependency tree. It also checks retained Wayland/KCM/test
settings, shared Qt/KF6 requirements and the missing native-generator guard.
This check does not compile or execute Fcitx5.

## Installed keyboard data paths

The recipe separates configure-time discovery paths from installed data paths.
IsoCodes and XKeyboardConfig discovery retains host sysroot paths and its checks.
Three `*_RUNTIME` CMake variables populate `config.h` with installed provider paths.
The original discovered values remain unchanged. Native defaults remain available.
The Xwayland session script is installed as an example and registered with `CONF_FILES`.
Package updates preserve a locally edited session script.

Run `tests/runtime-data-paths.sh` with native BMAKE and CMAKE, the prepared pkgsrc,
its MAKECONF, the verified Fcitx archive, and a new result directory.
The check reproduces the original sysroot leak and validates the patched header.
It checks native and cross recipe metadata and unchanged host discovery values.
Its missing-file case checks the host-path contract, not the complete upstream
Find-package sequence. No C/C++ analysis or target execution is claimed by this check.

## Cross-built test fixtures

`FCITX5_TEST_SOURCE_DIR` and `FCITX5_TEST_BINARY_DIR` are optional CMake cache paths.
They select the source and generated-data roots used by test executables at runtime.
Set both to absolute target paths when preparing a transferred test payload.
Native defaults remain the actual source and build directories.
These options change only `testdir.h`; build rules, assertions and installed programs stay unchanged.

`tests/test-fixture-paths.sh SOURCE RECIPE NEW_OUTPUT` uses the actual header configuration block.
Set CMAKE to the native CMake executable.
The check preserves the native header bytes and tests cross overrides, cache persistence and six invalid paths.
It does not compile or execute Fcitx tests.

The [runtime test payload](tests/runtime/README.md) retains all 51 registered upstream cases.
It uses these fixture roots and installed production libraries.
Its source, inventory and rejection checks pass on the build host.
The nb4 CM5 run passes 50 cases and fails the stronger XKB content check.
The nb5 patch retains parsed keyboard models and option groups.
The [real-source regression](tests/xkbrules.md) passes natively and with ASan/UBSan.
The original source fails both runs. The complete nb5 target suite remains pending.

## Library file-data regression

The inherited `Library::findData()` file path advanced a null search result.
It then called the parser and reported success when the signature was absent.
The patch returns false without calling the parser and retains the common
`munmap` path. The existing SunOS namespace guards remain.

Run the separate regression against a prepared native Utils build:

```sh
sh tests/library-find-data.sh /absolute/fcitx5-5.1.23 \
    /absolute/native-build /absolute/fcitx5-recipe /absolute/new-results
```

The script uses the build's compilation database, compiler and static library.
It rebuilds only the original and patched Library translation units and the
regression. Use the matching native build again for an ASan/UBSan run.
Do not mix an instrumented library with a different compiler's sanitizer runtime.

Native and ASan/UBSan runs pass on macOS. The original source fails both runs.
The cases cover a file signature, a loaded symbol, and two missing signatures:
a short file and a file longer than the signature. The separate GCC16 regression
also passes against installed nb4 libraries on CM5 under an ordinary user.
That target run is not an ASan, UBSan, Valgrind or leak-checking result.

Scoped Clang 23 analysis covers `library.cpp`, `isocodes.cpp` and `xkbrules.cpp`
with the actual GCC16/AArch64 build configuration and target headers.
It reports no diagnostics before or after this fix; runtime regression remains
necessary. Cppcheck 2.22 cannot evaluate `__has_cpp_attribute` with the captured
GCC built-ins, so its analysis remains incomplete. No diagnostic suppression
was added. Valgrind and leak checking were not performed.

## Relocatable CMake exports

Utils, Config, and Core export relative install-interface header directories.
Module configurations use `configure_package_config_file` and `PATH_VARS`.
Installed consumers can resolve headers through a staging sysroot or moved prefix.
Build-interface paths stay unchanged. The patches do not change C++ code or ABI.

Run `tests/cmake-exports.sh` with native CMAKE, the source archive, an unfixed
installed Fcitx prefix, and a new output directory. It first reproduces the
installed export failure. A `LANGUAGES NONE` fixture then uses the exact source
install-interface expressions, real Config templates, and upstream module macro.
It checks Utils, Config, Core, and Emoji after `DESTDIR` installation and a move.
Separate negative controls cover the original library and module exports.
These are metadata and header-location checks. They do not compile or run C++.
The complete rebuilt package and Qt consumer remain separate acceptance gates.
