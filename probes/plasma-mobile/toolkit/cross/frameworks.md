# Cross-building Frameworks 6.31

The common Qt 6.12 / GCC16 sysroot now cross-builds **KI18n, KCoreAddons and
KConfig 6.31.0**, plus KCodecs, KGuiAddons and KWindowSystem, through ordinary
pkgsrc package checks. The complete target
packages retain translations, headers, QML plugins and development metadata.
CM5 runtime checks now cover generated configuration persistence, file events
and locale lookup. The [model and worker-queue suites](models-and-jobs.md) also pass on CM5. The Plasma session remains unaccepted. See the [migration sequence](../MIGRATION.md).

## Native generators and target paths

ECM queries `qtpaths` from the native Qt during a cross build. Its answers
must not become target installation directories. The common `kf6.mk` selects
relative `qt6/plugins`, `qt6/qml`, `qt6/metatypes` and `qt6/doc` destinations.
`tests/selection.sh` exercises the production cross/native selection; normal
package checks verify actual staged files.

With the relative metatypes directory, exported CMake targets name
`${_IMPORT_PREFIX}/qt6/metatypes/*.json` as interface sources. A consumer
finds the provider below its buildlink prefix, so each KDE provider lists
its metatypes files in `BUILDLINK_FILES`. Without them, KCrash fails at CMake
generation unless another dependency, such as Declarative, links the whole
directory. `python3 -B tests/kde-metatypes-buildlink.py` checks every toolkit
KDE recipe that installs metatypes.

KCoreAddons, KConfig, KCodecs, KDBusAddons and KArchive use QtTools only for translation
generators. Their [Linguist helper](../../../../pkgsrc/devel/qt6-qttools/linguist.mk)
imports the matching native component without adding host library search
prefixes. KCoreAddons and KConfig explicitly depend on target Declarative.
KWidgetsAddons additionally needs the complete target QtTools package for its
Designer plugin; Linguist alone is insufficient. Its full package and
[54 installed widget API cases](models-and-jobs.md#widget-apis-and-the-designer-plugin)
now pass. Native builds use their normal QtTools build dependency. This does
not replace the full QtTools target package acceptance.

```sh
BMAKE=/absolute/native/bmake MAKECONF=/absolute/cross-mk.conf \
sh probes/plasma-mobile/toolkit/tests/linguist-tools.sh \
    /absolute/prepared-pkgsrc /absolute/new-check
```

[KDocTools](doctools.md) and [Breeze](breeze.md) also use matching native generators.
[Designer plugins](designer-plugins.md) remain enabled in complete cross packages.

KConfig consumers also execute `kconfig_compiler` while building. Build that
native generator from the manifest's original KConfig archive:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
TAR=/absolute/native/bsdtar HOST_READOBJ=/absolute/native/llvm-readobj \
HOST_OBJECT_ARCH=aarch64 HOST_PYTHON=/absolute/native/python3 \
HOST_PACKAGE_PREFIX=/absolute/native-dependencies \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ JOBS=2 \
sh probes/plasma-mobile/toolkit/cross/build-kconfig-tool.sh \
    /absolute/verified-distfiles /absolute/host-qt/qtbase \
    /absolute/native-dependencies/share/ECM/cmake /absolute/new-kconfig-host
```

`HOST_QT` can also name an installed Qt 6.12.0 prefix. The builder requires
its Core, Xml and LinguistTools CMake modules and selects their exact paths.
The Qt Xml library must already exist; build a missing Xml target separately
under the Qt producer exclusive lock. The caller holds the canonical Qt host
prefix SDK context lock shared throughout this generator build. On Darwin, set
`HOST_RUNTIME_VIEW` and `HOST_SDK_SOURCE` and run the producer through the SDK
runtime launcher so its native build tools use the selected view. Missing
selected modules fail before CMake can find another host Qt.

The installed-prefix regression builds the real native tools and generates a
configuration class with an integer default. It rejects malformed XML and a
prefix without Xml. A separate dispatch fixture requires the existing Qt
build-tree path to request Xml and propagate build failure:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
TAR=/absolute/native/bsdtar HOST_READOBJ=/absolute/native/llvm-readobj \
HOST_OBJECT_ARCH=aarch64 HOST_PYTHON=/absolute/native/python3 \
HOST_PACKAGE_PREFIX=/absolute/native-dependencies \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ JOBS=2 \
ruby probes/plasma-mobile/toolkit/tests/kconfig-host.rb \
    /absolute/verified-distfiles /absolute/installed-qt \
    /absolute/sysroot/usr/pkg/share/ECM/cmake /absolute/new-host-check
```

The generated native tooling is under `new-host-check/built/tooling`.
These checks execute native macOS tools. They do not run target KConfig or
accept the complete Qt build-tree lifecycle. No upstream C++ source changes.

The private native build produces only the generator and its Qt Xml
prerequisite. GUI/QML/DBus remain enabled in the separate target package.
The generated `tooling/KF6Config` import contains only a native executable,
never host libraries. Package builds do not read it: the native Ports package
`devel/kf6-kconfig-compiler` builds `kconfig_compiler_kf6` and `kconf_update`
from the KConfig source, distinfo and patches and installs them with their
`KF6ConfigCompilerTargets` import below `TOOLBASE`. A cross build of any
KConfig consumer takes it as a `TOOL_DEPENDS` package through the KConfig
`buildlink3.mk` and passes `-DKF6_HOST_TOOLING=${TOOLBASE}/lib/cmake`.
`tests/kf6-native-tools.sh` checks this wiring.
The [KConfig consumer](../tests/kconfig-consumer/README.md) exercises actual
CMake generation and compiles generated code against the target package.

## Relocatable KWindowSystem exports

KWindowSystem 6.31.0nb1 fixes a failure in the installed KAuth consumer.
Its exported XCB include path was an absolute producer prefix. Replacing a
build path with `/usr/pkg/include` made the package clean but unusable when
imported from a cross sysroot. The port now exports `X11::xcb` as a public
requirement and asks each consumer to discover that dependency with FindX11.
It removes the previous path substitution and preserves X11 and Wayland.

`tests/windowsystem-import.rb INSTALLED_CMAKE_DIRECTORY SYSROOT NEW_WORK`
configures and cross-links a consumer including KKeyServer and XCB headers.
Set `CMAKE`, `CXX` and `QT_HOST_PATH` to the selected native CMake, cross
compiler and native Qt. The regression then restores a producer path in a
private export copy and requires CMake to reject it. Both paths pass on
2026-10-12. KAuth 6.31 also passes full packaging against the repaired export
and polkit-qt 0.201.1. This is consumer-build evidence, not a display test.

## Wayland protocol data and consumers

ECM 6.31.0nb1 resolves Wayland protocol XML through CMake's target root search.
A raw pkg-config data variable names the target prefix, which is not a usable
build-host path. `tests/wayland-protocol-paths.sh` exercises the actual module:
native lookup, cross lookup with a host trap, and rejection of missing target
XML all pass. Plasma Wayland Protocols uses current stable 1.23.0.
The toolkit also forwards the native Wayland scanner through both include orders.

Qt 6.12 supplies WaylandClient in Qtbase. KGuiAddons and KWindowSystem use that
component and explicit target Declarative/Wayland dependencies. KWindowSystem
also roots imported pkg-config XKB paths and removes the build sysroot from
its installed CMake export; normal package checks pass.

## KI18n locale data

The common graphics [iso-codes delta](../../../../profiles/common-graphics/cross/iso-codes-host-python.patch)
selects current stable 4.20.1 and upstream Meson. Its JSON, XML and translated
data are packaged; upstream's Python scripts are native build tools, not a new
target runtime dependency.

KI18n now declares `pkg-config` explicitly. Without its wrapper the build can
succeed with an empty `ISO_CODES_PREFIX`, leaving runtime country data absent.
The accepted configure defines `/usr/pkg` for locale and iso-codes prefixes;
the package records `iso-codes>=4.20.1` as a runtime dependency.

The common recipe uses the original Salsa release archive. Its pkgsrc digests
are in the common graphics delta.

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
fails on CM5: 259 tests report 231 passed, 12 failed and 16 skipped. Its
executable returns zero even on assertion failures, so journal totals must
also be checked. KDirWatch's explicit inotify suite loses six of 19 cases.

## Package evidence, 2026-10-12

On macOS/arm64 the following packages pass normal pkgsrc manifest,
interpreter, permission, PIE, RELRO, RPATH and work-directory checks and
installation into the common build sysroot. Native generators stay outside
that sysroot. No target executable was run on macOS.

| Package | SHA256 |
| --- | --- |
| KConfig 6.31.0 | `081eb45a9cb3152b400df4e84480942a3cd3c452fbf4dd1fceb8452192745ea2` |
| KCoreAddons 6.31.0nb1 | `aa93db410365580476e8ae4a91dbbd0c1942ee66a1623c2e1b0152c871c7ce8e` |
| libinotify 20240724 | `54ab21f3a971c554eab9833c2922b377a89e6bc8982be8bf8aba036cce48eeb0` |
| KI18n 6.31.0 | `7bb5ce8f0a90821ce12872afce50750f6976056070188c0c332ffe7a1702f0f9` |
| iso-codes 4.20.1 | `28a05cafc10a237147b029b7bbcd1ac830d034c1205e2bada0c951949f3d4983` |
| KCodecs 6.31.0 | `6300a10c28ccbd8ee025601d0e8fcd49e360f55bf80b9b9fa76fbec7c24c1d1e` |
| KGuiAddons 6.31.0 | `3d5a7a3b758bd559e2b4b2af4ad2178b7ede1fa91e5c55667fc2474b803b6b98` |
| KWindowSystem 6.31.0 | `a41d5d2d0f219c2761d56547c57459a2e9f438a0715eb03f03d75f8e99307cdd` |
| ECM 6.31.0nb1 | `921ba1dbe7796cc8b3fd1b6656953af1f0d68bb54c64d8b158e4e766c6e6771f` |
| Plasma Wayland Protocols 1.23.0 | `9a45d3e862101b16355815ffd4ea08e910f4ff1d4f7f3fa0b0de97562823224f` |

## Installed CM5 runtime

KCoreAddons nb1 selects Qt's native kqueue watcher by default on EmberBSD;
explicit inotify and polling choices remain available. The new default test
fails against the previous installed library and passes all **19 file-event
checks** against nb1 in 23.2 seconds. Explicit QFSWatch and Stat each pass
19 checks; this does not certify libinotify. Cppcheck with the actual compile
database and Qt model reports the same nine existing Entry-initializer
warnings before and after the patch. Entry is value-initialized in addEntry;
no new finding was introduced.

The [KConfig consumer](../tests/kconfig-consumer/README.md) passes generated
defaults, fresh-process writes/reads, a rejected wrong expectation and
interoperation with installed kreadconfig6/kwriteconfig6. KFormat's installed
QML import passes its three assertions with the upstream QML fixture.

KI18n's original country suite first failed because the base libintl applied
Welsh plural selection to ordinary translations. The
[EmberBSD libintl fix](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/libintl-validation.md)
passes 200 shared/static assertions and restores all 22 country checks without
changing their expectations. Subdivision, timezone and declarative suites
pass 13, 19 and 15 checks. Legacy KLocalizedContext rows still emit singleton
warnings; this is not a warning-free localization acceptance.

Copy the relevant original Frameworks test binaries from the cross build,
including the patched `kdirwatch_default_unittest`, to a private target directory:

```sh
sh probes/plasma-mobile/toolkit/tests/frameworks-runtime.sh \
    /absolute/upstream-test-binaries /absolute/new-results
```

The runner isolates settings, bounds each process and checks that no reboot
occurred. It uses software QML for API tests and makes no GPU claim.
The board is CM5 Rev 1.0/BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B, running kernel
SHA256 `6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.
These short checks do not establish desktop latency or long-duration stability.

KCoreAddons' inherited shared-cache implementation warns that POSIX timeout
support is not advertised. A normal cache test alone cannot establish recovery
from a crashed writer. Its four assertions pass only after falling back to
anonymous memory; file-backed shared-cache operation is not accepted. The
remaining Frameworks runtimes, full QtTools and Plasma are still separate gates. Valgrind has no validated EmberBSD/AArch64 path here.

Sources: [Frameworks 6.31](https://kde.org/announcements/frameworks/6/6.31.0/),
[iso-codes tags](https://salsa.debian.org/iso-codes-team/iso-codes/-/tags),
[libinotify release](https://github.com/libinotify-kqueue/libinotify-kqueue/releases/tag/20240724).
