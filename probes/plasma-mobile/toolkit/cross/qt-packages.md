# Qt 6.12 target package acceptance

The AArch64 Qtbase runtime and SDK pass independent full GCC 16.2 builds,
complete upstream staging, manifest partition checks and ordinary pkgsrc QA.
The runtime installs on EmberBSD and the SDK installs in the cross sysroot.
The installed [Core/Gui/SVG consumer](../tests/qt-consumer/README.md) configures
and links through the packaged Qt CMake entry point and matching native tools.
The SDK is not installed on the target board.

Qtbase buildlink reads pkgsrc preferences before it selects the cross SDK.
An ordinary libdbusmenu-lxqt build exposed the previous ordering error:
`QEvent` existed in the installed SDK but was absent from buildlink. Reading
preferences first adds `qt6-qtbase-devel>=6.12.0nb3` to `BUILD_DEPENDS` and the
buildlink tree. The actual before/after metadata checks also confirm that it
stays out of runtime `DEPENDS`, and native mode does not select the target SDK.
This metadata check is separate from the consumer package build.

## Packages and provenance

The [toolkit manifest](../sources.tsv) pins the original Qt 6.12 archives and
SHA256. The base pkgsrc revision is
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Target objects use the common
GCC 16.2 toolchain and EmberBSD sysroot. Host generators use Qt 6.12.0.
Prefixes remain `/usr/pkg` and `/usr/pkg/qt6`.

| Package | SHA256 |
| --- | --- |
| qt6-qtbase-6.12.0nb2.tgz | `fcba145913e274c288ea27fadaac4297f37c22ead5c801732bad5b0733987320` |
| qt6-qtbase-devel-6.12.0nb3.tgz | `2fa0da3ee5ee167e1fdb83ff69b55a8664b50f08d2d20cdb46b0410d95de67cc` |
| qt6-qtsvg-6.12.0.tgz | `7a4e524ed141f77b1977b1c6079e9e4c007577f21c365d0d81939c9305a8e903` |
| qt6-qtshadertools-6.12.0.tgz | `44c8f7a86d8649b0d28b2a310e9f876e426e6ef8f7fa163dbebfe017d6c2f0f5` |
| qt6-qtimageformats-6.12.0.tgz | `e305054f67451b546e08577dfcfe97ecf2416c4fabf643d585b169582909fdb3` |
| qt6-qtlanguageserver-6.12.0.tgz | `7588f28ef7a9c3882df644d973e28014b342ad5f0e322502356d0a8a5b4c8ee0` |
| qt6-qtdeclarative-6.12.0.tgz | `741d97e690647a91b36c5ca08f91d036914340a9db766add278c5c4ba9206911` |
| qt6-qttools-6.12.0nb2.tgz | `07846c3c84fae12bdff27046fe8fc60c4d7148b51f9f7b8f4e2a92cb2fe0a21b` |

Qtbase runtime compilation uses Ports `dc73cc6`, which includes the detached
process correction. The SDK Qtbase recipe and patches use clean `fcf13a1`, including the scanner
error-path correction. The SDK packaging recipe is `60cdaf6`. That recipe makes
EGLDevice a required modern-profile feature and fixes early/late manifest
expansion. Its original compiled cache already has EGLDevice enabled; the
compile did not receive the later required CMake argument. Restaging uses all
compiled objects and the ordinary complete package lifecycle.

Each full Qtbase build has 1,463 entries in its actual compilation database.
Both preserve all 468 unique configured feature definitions. The 13 runtime
DSO export sets are unchanged from the previous full package. QtCore retains
its SONAME and 7,588 dynamic exports. Runtime and SDK Core code sections match.
All 2,702 installed SDK include entries match the previous full package.

## Package and sysroot checks

The [runtime/SDK contract](qtbase-runtime.md) requires disjoint ownership and
complete coverage of the full manifest. The runtime has 131 file or symlink
payload entries and 55 AArch64 ELF files. It contains no SDK headers, static
archives, CMake metadata or target generators. The SDK requires the exact
runtime package. Archive audits verify each payload checksum, mode and symlink,
ELF architecture, static archive members and install-helper paths.

Normal interpreter, permission, PIE, RELRO, RPATH and work-directory checks pass.
Both packages install through normal package tools in the cross sysroot.
Installed payload bytes, modes and symlinks match their archives. Public Qt
package directories have mode 0755. Scope umask 022 around package installation
as described in [the installation contract](qtbase-runtime.md#build-and-installation).

The real CMake consumer uses the installed `qt-cmake`, target headers and
libraries, native Qt 6.12 generators, and GCC 16.2. Its finite Core/Gui/SVG
scenario checks resource data, queued worker signals, SVG pixels, image plugins,
PNG round trips and rejected invalid inputs. Direct execution of this exact
new executable passes four finite cycles on EmberBSD with the installed runtime.
This accepts the SDK-to-runtime ABI for that scenario; the target has no SDK or
qmake installation. The broader package removal/restart wrapper is separate.

## Installed runtime checks

The [private mutex consumer](../tests/qt-mutex/README.md) checks descriptor use
under contention. The previous library reached the descriptor limit; the fixed
library retains three descriptors with 145 workers. The
[process matrix](../tests/qt-process/README.md) checks 320 child exits and 16
failed launches with the installed runtime. The
[Wayland/EGL consumer](../tests/qt-wayland-gl/README.md) checks V3D shader pixels
and repeated processes. The [Qt Quick consumer](../tests/qt-quick-gpu/README.md)
checks compiled QML scene and layer pixels through V3D.

The installed [Plasma virtual-output runner](../tests/plasma-session/README.md)
passes two complete sessions with readiness at 18.407673 and 15.660989 seconds,
30 seconds of liveness, normal logout near 2.037 seconds and desktop pixels.
GPU buffer use returns to its baseline with no recorded allocation failure.
These are virtual-output GPU results. They do not accept physical HDMI, display
hotplug, input devices or long-duration stability.

## Other module checks

The [TextToSpeech consumer](../tests/qt-speech/README.md) passes Flite PCM
synthesis and speech-dispatcher/eSpeak service lifecycles.
[KCMUtils](kcmutils.md) passes its generated-settings target check.
The [Multimedia player](../tests/qt-multimedia/README.md) passes exact video
frames, end of media, restart and rejected invalid input with FFmpeg 9.0.2.
Quick3D passes host OBJ import and generated QML bytecode; target Quick3D scenes
and spatial audio remain unaccepted.

QtTools retains Designer, Assistant, Help, UiTools, Linguist and Clang-backed
QDoc. Assistant requires the common shared litehtml provider. The
[provider regression](../tests/qttools-provider.rb) rejects silent bundled
fallback and checks installed ELF dependencies. The unchanged
[QDoc consumer](../tests/qdoc/run.sh) generates C++ class and member HTML,
checks index content and rejects missing configuration on EmberBSD. This does
not accept Assistant or Designer windows. Native QDoc uses the same LLVM/Clang
23.1.3 release and passes host documentation generation.

## Analysis and dependency limits

The scanner correction has actual missing-input and invalid-XML regressions.
The original missing-input path terminates with SIGSEGV. The patched path
returns status 1. Cppcheck 2.22 reports the same 11 reviewed findings before and
after the patch. Clang Static Analyzer 21 reports no findings in either version.
Native ASan/UBSan reproduces the original null access and passes the corrected
valid and invalid cases. This analysis covers the real native scanner source
and compile options. It does not establish memory safety for all target Qt.
Valgrind has no validated EmberBSD/AArch64 execution path.

Both full builds retain the same compiler diagnostics in Qt's cryptographic
hash code, QDebug template completion and base libutil compatibility references.
They are unconfirmed inherited findings, not a clean compiler-warning claim.
The SDK retains the upstream executable-bit warning for
`qt_cyclonedx_generator.py`. No diagnostic category is suppressed.

The runtime dependency audit resolves 90 installed package nodes and all 64
external required library paths to one provider each. That metadata closure
is not a complete offline package set or an execution-only image closure.
The recipe still requires the full GCC 16 package and Python 3.15; the libproxy
path also retains Python 3.14 through gobject-introspection.

The pkg-vulnerabilities database revision 1.805 reports four inherited
advisories: Expat 2.8.5 CVE-2025-66382 through DBus, and Python 3.14.8
CVE-2025-15367, CVE-2025-12781 and CVE-2026-3479 through libproxy and
introspection. The audit exits 1. No vulnerability bypass is enabled.
These advisories are separate from the Qt process correction. The packages
and image closure are not declared vulnerability-clean.

## Reproduction

Prepare the [common cross configuration](README.md#target-package-build).
Use ordinary `bmake package` and `bmake install` for a new package, or `replace`
for an installed sysroot update. Build Qtbase runtime before its exact SDK.
Use separate `install-clean` and `repackage` calls for a packaging-only repair;
`repackage` recreates the stage and retains compiled objects. Keep host and
target package databases and package output directories separate.

The [source packaging checks](qtbase-runtime.md#source-packaging-checks) cover
manifest ownership, early and late EGLDevice state, seven rejected invalid
stages, exact dependency matching and ordinary package replacement/removal.
The [mkspecs check](../tests/mkspecs-preservation.sh) preserves generated metadata
and licensing. The [target metadata check](../tests/target-metadata.sh) rejects
host compiler paths and verifies relocatable CMake exports. Fixtures complement
the actual package builds and consumers; they do not execute target Qt.
