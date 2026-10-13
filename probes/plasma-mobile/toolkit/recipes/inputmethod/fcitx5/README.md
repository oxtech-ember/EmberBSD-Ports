# Fcitx5 source candidate

These recipes select the official September 23, 2026 releases:
Fcitx5 5.1.23, Fcitx5 Qt 5.1.16 and Configtool 5.1.16.
The latter two use the common Qt 6.12 and Frameworks 6.31 providers.
Configtool retains its KDE control module and standalone configuration UI.
The core retains Wayland, X11, Enchant, keyboard, emoji, spell and tests.
The Qt adapter retains its Wayland integration.

This is a source candidate. No complete package or target input session has
been accepted. The PLIST files need comparison with real staged payloads.
Cppcheck, path analysis and target memory checks remain unperformed.
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
