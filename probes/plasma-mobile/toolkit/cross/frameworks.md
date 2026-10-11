# Cross-building Frameworks 6.31

The common Qt 6.12 / GCC16 sysroot now cross-builds **KI18n, KCoreAddons and
KConfig 6.31.0** through ordinary pkgsrc package checks. The complete target
packages retain translations, headers, QML plugins and development metadata.
This is package acceptance; the installed Frameworks tests and Plasma session
still need CM5 execution. See the [migration sequence](../MIGRATION.md).

## Native generators and target paths

ECM queries `qtpaths` from the native Qt during a cross build. Its answers
must not become target installation directories. The common `kf6.mk` selects
relative `qt6/plugins`, `qt6/qml`, `qt6/metatypes` and `qt6/doc` destinations.
`tests/selection.sh` exercises the production cross/native selection; normal
package checks verify actual staged files.

KCoreAddons, KConfig, KCodecs and KWidgetsAddons use QtTools only for translation
generators. Their [Linguist helper](../recipes/devel/qt6-qttools/linguist.mk)
imports the matching native component without adding host library search
prefixes. KCoreAddons and KConfig explicitly depend on target Declarative.
The native recipe still uses its normal QtTools build dependency. This does
not replace the full QtTools target package or its QDoc/Clang acceptance.

```sh
BMAKE=/absolute/native/bmake MAKECONF=/absolute/cross-mk.conf \
sh probes/plasma-mobile/toolkit/tests/linguist-tools.sh \
    /absolute/prepared-pkgsrc /absolute/host-qt/qtbase /absolute/new-check
```

KConfig consumers also execute `kconfig_compiler` while building. Build that
native generator from the manifest's original KConfig archive:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ JOBS=2 \
sh probes/plasma-mobile/toolkit/cross/build-kconfig-tool.sh \
    /absolute/verified-distfiles /absolute/host-qt/qtbase \
    /absolute/sysroot/usr/pkg/share/ECM/cmake /absolute/new-kconfig-host
```

The private native build produces only the generator and its Qt Xml
prerequisite. GUI/QML/DBus remain enabled in the separate target package.
The generated `tooling/KF6Config` import contains only a native executable,
never host libraries. Add to the private MAKECONF:

```make
EMBERBSD_KF6_HOST_TOOLING=/absolute/kconfig-host/tooling
```

The toolkit forwards both Qt and KF host paths even when assigned after
including the profile. `tests/consumer-host-tools.sh` checks both include
orders, paths containing spaces, unset variables and native-tool sub-builds.
The [KConfig consumer](../tests/kconfig-consumer/README.md) exercises actual
CMake generation and compiles generated code against the target package.

## KI18n locale data

The `iso-codes` recipe selects current stable 4.20.1 and upstream Meson.
Its complete JSON, XML and translated data are packaged; upstream's Python
scripts are native build tools, not a new target runtime dependency.
All eight upstream UTF-8 checks pass on the host.

KI18n now declares `pkg-config` explicitly. Without its wrapper the build can
succeed with an empty `ISO_CODES_PREFIX`, leaving runtime country data absent.
The accepted configure defines `/usr/pkg` for locale and iso-codes prefixes;
the package records `iso-codes>=4.20.1` as a runtime dependency.

The original Debian archive SHA256 matches the official `.dsc` record.
This is checksum comparison, not signature verification. Provenance is in
[sources.tsv](../sources.tsv), with pkgsrc digests in the recipe.

## libinotify target measurements

KCoreAddons uses libinotify-kqueue 20240724, the current stable upstream release.
Its native configure executes kqueue and path-descriptor probes. Cross builds
now require their **measured target answers**, rather than host guesses.
The [target probe](../tests/libinotify/target-features.c) is adapted from
upstream configure and retains its authorship and MIT licence.

```sh
CROSS_CC=/absolute/cross-gcc
"$CROSS_CC" --sysroot=/absolute/ember-sysroot -O2 -Wall -Wextra \
    probes/plasma-mobile/toolkit/tests/libinotify/target-features.c \
    -o /absolute/target-features
```

Copy the ELF to the target and run with a timeout in a fresh writable directory.
Only a successful exit and all five output lines constitute a measurement.
For the accepted CM5 V3D kernel `e3dd93954fa7fde09e9da0667cb67b7e0c3544e91719be8dfc05e478cd9deea4`,
the result was:

```make
.if ${PKGPATH} == "devel/libinotify"
CONFIGURE_ENV+= ember_cv_note_extend_to=yes ember_cv_note_extend_from=no
CONFIGURE_ENV+= ember_cv_o_path=no ember_cv_o_empty_path=no ember_cv_at_empty_path=no
.endif
```

Keep these values in the private MAKECONF with the measured kernel identity.
Recheck after a relevant kernel/libc change. The measurement does not certify
all inotify semantics; symlink-only watches remain limited without O_PATH or
O_SYMLINK. Configure still uses the original runtime probes for native builds.

`tests/libinotify/cross-configure.sh CONFIGURED_SOURCE NEW_WORK` copies the
real generated configure source and checks missing/invalid values for all
five cross probes. Set target `CC`, `CXX`, `AR`, `RANLIB`, sysroot compiler/linker
flags, `BUILD_TRIPLET` and `TARGET_TRIPLET` as for the accepted package.
Ten negative cases pass. The target feature probe also passes GCC16
`-fanalyzer` compilation and Cppcheck 2.22. Full libinotify runtime acceptance
remains pending; its upstream test executable returns zero even on assertion
failures, so the journal's Failed/Skipped totals must also be checked.

## Package evidence, 2026-10-12

On macOS/arm64 the following packages pass normal pkgsrc manifest,
interpreter, permission, PIE, RELRO, RPATH and work-directory checks and
installation into the common build sysroot. Native generators stay outside
that sysroot. No target executable was run on macOS.

| Package | SHA256 |
| --- | --- |
| KConfig 6.31.0 | `081eb45a9cb3152b400df4e84480942a3cd3c452fbf4dd1fceb8452192745ea2` |
| KCoreAddons 6.31.0 | `c487b453c7b0a94f73c98b642cda9f527652878bfa27761e1ca556c43c22fe0e` |
| libinotify 20240724 | `54ab21f3a971c554eab9833c2922b377a89e6bc8982be8bf8aba036cce48eeb0` |
| KI18n 6.31.0 | `7bb5ce8f0a90821ce12872afce50750f6976056070188c0c332ffe7a1702f0f9` |
| iso-codes 4.20.1 | `28a05cafc10a237147b029b7bbcd1ac830d034c1205e2bada0c951949f3d4983` |

KCoreAddons' inherited shared-cache implementation warns that POSIX timeout
support is not advertised. A normal cache test alone cannot establish recovery
from a crashed writer. Cache recovery, file watching, localization, installed
QML imports, the full QtTools package and the Plasma session remain separate
runtime gates. Valgrind has no validated EmberBSD/AArch64 path here.

Sources: [Frameworks 6.31](https://kde.org/announcements/frameworks/6/6.31.0/),
[iso-codes tags](https://salsa.debian.org/iso-codes-team/iso-codes/-/tags),
[Debian source record](https://deb.debian.org/debian/pool/main/i/iso-codes/iso-codes_4.20.1-1.dsc),
[libinotify release](https://github.com/libinotify-kqueue/libinotify-kqueue/releases/tag/20240724).
