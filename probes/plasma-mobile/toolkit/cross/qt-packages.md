# Qt 6.12 target package acceptance

On 2026-10-11, Qtbase, SVG, ShaderTools, ImageFormats and LanguageServer 6.12.0 cross-built on macOS/arm64
for EmberBSD/AArch64. All five passed normal pkgsrc staging, manifests,
interpreter/permission, PIE, RELRO, RPATH and work-directory checks. They
installed in the fork's build sysroot through pkg_add; Qtbase also passed
ordinary package replacement after its CMake metadata correction.

The installed [Core/Gui/SVG consumer](../tests/qt-consumer/README.md) also passes
on CM5, including real image pixels, plugin rejection, restart and SVG package
removal/reinstallation. qmake version lookup passes. Quick, accelerated Qt
rendering, other module runtimes and Plasma remain unaccepted.

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

## Reproduction and remaining runtime checks

Prepare the [common cross configuration](README.md#target-package-build),
then use ordinary bmake package/install in `x11/qt6-qtbase`,
`graphics/qt6-qtsvg`, `graphics/qt6-qtshadertools`, `graphics/qt6-qtimageformats`\nand `lang/qt6-qtlanguageserver`. Keep host and target
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
