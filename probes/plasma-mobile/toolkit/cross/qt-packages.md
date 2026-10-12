# Qt 6.12 target package acceptance

On 2026-10-11–12, Qtbase, SVG, ShaderTools, ImageFormats, LanguageServer and Declarative 6.12.0 cross-built on macOS/arm64
for EmberBSD/AArch64. All six passed normal pkgsrc staging, manifests,
interpreter/permission, PIE, RELRO, RPATH and work-directory checks. They
installed in the fork's build sysroot through pkg_add; Qtbase also passed
ordinary package replacement after its CMake metadata correction.

The installed [Core/Gui/SVG consumer](../tests/qt-consumer/README.md) also passes
on CM5, including real image pixels, plugin rejection, restart and SVG package
removal/reinstallation. qmake version lookup passes. The [Wayland/EGL consumer](../tests/qt-wayland-gl/README.md) also passes V3D
shader pixels and repeated processes on CM5. The [Qt Quick consumer](../tests/qt-quick-gpu/README.md)
also passes compiled QML scene/layer pixels through V3D. Other module runtimes
and Plasma remain unaccepted.

## TextToSpeech and KDE settings

The [installed TextToSpeech consumer](../tests/qt-speech/README.md) passes both
Flite PCM synthesis and speech-dispatcher/eSpeak service lifecycles on CM5.
[KCMUtils](kcmutils.md) now cross-packages with explicit native metadata tooling;
its generated-settings test passes on the board. Full Plasma remains unaccepted.

## Quick3D and Multimedia packages

Quick3D and Multimedia 6.12.0nb1 now cross-package and install with their full
selected payloads. The [installed player check](../tests/qt-multimedia/README.md)
passes exact video frames, end of media, process restart and failure controls
on CM5 with FFmpeg 9.0.2. Quick3D host OBJ import and generated QML bytecode
also pass. Target Quick3D scenes, spatial audio and full Plasma remain unaccepted.

## Full QtTools package

QtTools 6.12.0nb2 also passes the ordinary complete package checks and installs
in the same build sysroot. Designer, Assistant, Help, UiTools, Linguist and
Clang-backed QDoc remain present; no component or package check is disabled.
The manifest includes the new Designer private headers and QDoc conversion
and generator headers declared by upstream Qt 6.12.

Assistant links the common shared `liblitehtml.so.0`. The recipe enables the
upstream system-provider option and makes its `find_package` required, so a
missing dependency cannot silently select the bundled copy. The real selection
regression reproduces the old silent behavior, rejects a disabled required
provider and checks installed Assistant/QDoc ELF dependencies.

```sh
BMAKE=/absolute/native/bmake CMAKE=/absolute/native/cmake ruby \
    tests/qttools-provider.rb /absolute/pkgsrc /absolute/cross.mk.conf \
    /absolute/configured-qttools /absolute/sysroot \
    /absolute/cross-readelf /absolute/new-results
```

The test path above is relative to this toolkit. Package SHA256:
`07846c3c84fae12bdff27046fe8fc60c4d7148b51f9f7b8f4e2a92cb2fe0a21b`.
The full package was rebuilt against LLVM/Clang 23.1.3 and replaced in the
common sysroot on 2026-10-12. The shared-provider regression passes again;
package metadata requires Clang >=23.1.3. Normal CM5 installation and package-file
checks also pass. The unchanged `tests/qdoc/run.sh` consumer creates C++ class
and member HTML through the installed Clang-backed QDoc, checks index content,
and rejects missing configuration. CM5 result archive SHA256:
`3ba618ab65c42f065d12549e75a84f358ca932f9f0be9de6eaceee396e78daa1`.
This validates target documentation generation, not Assistant/Designer windows
or the complete QtTools runtime.
[Native QDoc](README.md) also uses 23.1.3
and independently passes real C++ documentation generation on the build host.

## Inputs and packages

The [toolkit manifest](../sources.tsv) pins original Qt 6.12 archives and
SHA256. The base pkgsrc revision is `fff4deb639a1a640476203c80f752fb77b6cb14b`.
The [host generators](README.md) use the same Qt release. The target uses
GCC 16.2, the verified fork sysroot, CMake 4.4.4, Mesa 26.2.4nb3,
libdrm 2.4.134nb2 and the common LLVM23 stack. Final prefixes remain
`/usr/pkg` and `/usr/pkg/qt6`; no older target Qt is added.

| Package | SHA256 |
| --- | --- |
| qt6-qtbase-6.12.0.tgz | `909725fe2cdbf3159ca368c9b6e39747b27e16a69a580286a00d661c675d5151` |
| qt6-qtsvg-6.12.0.tgz | `7a4e524ed141f77b1977b1c6079e9e4c007577f21c365d0d81939c9305a8e903` |
| qt6-qtshadertools-6.12.0.tgz | `44c8f7a86d8649b0d28b2a310e9f876e426e6ef8f7fa163dbebfe017d6c2f0f5` |

ImageFormats SHA256: `e305054f67451b546e08577dfcfe97ecf2416c4fabf643d585b169582909fdb3`
for `qt6-qtimageformats-6.12.0.tgz`. All seven image plugins are packaged.

LanguageServer SHA256: `7588f28ef7a9c3882df644d973e28014b342ad5f0e322502356d0a8a5b4c8ee0`
for `qt6-qtlanguageserver-6.12.0.tgz`. It built and installed through ordinary
dependency recursion before Declarative configuration.

Declarative SHA256: `741d97e690647a91b36c5ca08f91d036914340a9db766add278c5c4ba9206911`
for `qt6-qtdeclarative-6.12.0.tgz`. Both sysroot installation and ordinary
installation on CM5 pass; the linked consumer uses only the common stack.

Qtbase retains one upstream permission warning: `qt_cyclonedx_generator.py`
has an executable bit without a shebang. No package check was disabled to
produce these results. The inherited Python build/runtime dependencies remain.

## Corrections exercised by actual builds

The old pre-configure loop copied qmake.conf over every mkspecs entry,
including generated qmodule.pri and the REUSE license manifest. It also
created fake configurations in common/features/modules/unsupported directories.
The corrected loop changes only existing platform configurations. The regression
runs the actual recipe loop twice, preserving metadata and licensing each time;
it fails with the original recipe. Existing damaged work trees need restoration
of the license file from the verified archive and regeneration of qmodule.pri.
Do not discard compiled objects merely to repair these files.

Cross Qt installs target development tools and libraries, but upstream omits
Android deployment host tools. The manifest reflects that distinction and the
actual Qt 6.12 headers/protocol files. SVG's renamed private paint-server header
also replaces the obsolete entry. Native-host manifests remain separately untested.

The installed SDK must not retain build-host qmake wrappers, preliminary CMake
files or build-root compiler paths. `files/target-metadata.pl` in the Qtbase
recipe normalizes those generated files, keeps target tools and writes a
relative qt.conf. Module packages use the same checked metadata conversion.
Unexpected remaining work/sysroot paths cause installation to fail.

A real SVG cross build then exposed CMake's imported-target behavior: absolute
`/usr/pkg/include` is checked on the build host before compiler wrappers run.
Qt's exported platform include/library directories now resolve relative to its
installed prefix. SVG and ShaderTools configure and compile against this
installed Qtbase, using native generators and target libraries. The common
recipe invokes the module configuration script from the selected sysroot.

Qt 6.12 disables automatic selection of JasPer and MNG. The unchanged
manifest required their plugins although configuration found the libraries
and left both features off. The recipe now explicitly requires both features.
The real rebuild includes QJp2Plugin/QMngPlugin and passes the full package
manifest; no codec entries or package checks were removed.

Qt 6.12 moves QmlLint headers out of QmlCompiler, adds QmlDesignSupport,
Native/FluentWinUI3 controls and other development files. Declarative's manifest
now follows actual staging; no component was dropped to pass packaging.
Cross target QmlTime metadata uses the upstream `_native.qmltypes` name,
while the native-build branch retains its unsuffixed name. Native packaging
remains untested. The inherited AArch64 JIT policy remains disabled.

## Reproduction and remaining runtime checks

Prepare the [common cross configuration](README.md#target-package-build),
then use ordinary bmake package/install in `x11/qt6-qtbase`,
`graphics/qt6-qtsvg`, `graphics/qt6-qtshadertools`, `graphics/qt6-qtimageformats`
`lang/qt6-qtlanguageserver` and `lang/qt6-qtdeclarative`. Keep host and target
package databases and output directories separate. For a packaging-only repair,
`install-clean plist-clean` regenerates staging and manifests while retaining
compiled objects. Use the normal `replace` target when updating an installed
sysroot package.

```sh
BMAKE=/absolute/native/bmake sh \
    probes/plasma-mobile/toolkit/tests/mkspecs-preservation.sh \
    probes/plasma-mobile/toolkit/recipes/x11/qt6-qtbase /absolute/new-loop-test
sh probes/plasma-mobile/toolkit/tests/target-metadata.sh \
    probes/plasma-mobile/toolkit/recipes/x11/qt6-qtbase /absolute/new-metadata-test
```

The metadata checks cover native tool paths, relocatable CMake exports, preserved
executable permissions, repeat installation, module-only staging and rejection
of an unhandled build path. Actual module compilation supplies the CMake
consumer check; fixture success alone would not prove it.

Next follow the [migration sequence](../MIGRATION.md): target EGL/OpenGL
consumers, Quick/Wayland, then HDMI Plasma and remote acceptance. The completed
Core/resource and SVG/plugin checks are scoped in their receipt. Memory analysis of target Qt execution remains pending; Valgrind
has no validated EmberBSD/AArch64 path. These package checks are not a Valgrind,
upstream Qt test-suite or accelerated-desktop pass.
