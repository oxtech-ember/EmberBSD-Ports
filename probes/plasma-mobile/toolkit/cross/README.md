# Cross-building the common Qt toolkit

The target is the shared Qt 6.12.0 package set for EmberBSD/AArch64, using
GCC 16.2 and the current common Mesa/LLVM providers. The build host may be
macOS. A host generator is a build prerequisite, not a second target Qt.
The final target prefix remains `/usr/pkg/qt6`.

## Native generators

Use the four original Qt archives in [sources.tsv](../sources.tsv): qtbase,
qtshadertools, qtdeclarative and qttools. The host recipe verifies their
SHA256 before extracting anything. It builds unmodified upstream sources;
EmberBSD target portability patches are applied separately by pkgsrc.

Qt requires matching host and target versions. An installed Qt 6.11 toolkit
cannot generate a Qt 6.12 build. See the
[upstream cross-build instructions](https://doc.qt.io/qt-6/cross-compiling-qt.html).

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
WAYLAND_SCANNER=/absolute/wayland-1.26/bin/wayland-scanner \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ JOBS=4 \
sh probes/plasma-mobile/toolkit/cross/build-host-tools.sh \
    /absolute/verified-distfiles /absolute/new-host-qt
```

Set `TMPDIR` and choose `JOBS` from the available host memory and storage.
The recipe keeps per-module configure/build logs, input hashes and tool hashes.
A failed command stops the build. It neither installs target packages nor
reports an accelerated session.

Use `RESUME=1` with the same arguments after correcting a build failure.
The recipe checks the selected tool hashes and all four archives again,
preserves earlier logs and reuses existing sources and objects. Do not edit
those extracted sources; choose a new work directory to change inputs.

On macOS, Qt's portable `qtwaylandscanner` requires an explicit native
Wayland scanner and `QT_FIND_ALL_PACKAGES_ALWAYS=ON` during the initial
configure. Qt developer builds cache failed package searches. When diagnosing
an existing build, remove `QT_INTERNAL_PREVIOUSLY_FOUND_PACKAGES` with CMake's
`-U` before repeating discovery; setting the executable path alone is insufficient.

The separate host module builds also need the actual Qt libraries used by
their generators. Configured CMake package metadata alone is insufficient.
These host libraries stay in the private build tree. They are never copied
to the EmberBSD sysroot.

## Generator acceptance

On macOS, run the native generator check after building:

```sh
HOST_CXX=/absolute/native/c++ sh \
    probes/plasma-mobile/toolkit/cross/check-host-tools.sh \
    /absolute/host-qt/qtbase /absolute/new-generator-check
```

It compiles and runs a real QObject/resource/translation consumer, compiles
UI and QML registration output, generates a shader bundle, QML bytecode
and Wayland headers, and rejects invalid shader/QML inputs. It does not
run a GUI or establish target Qt compatibility. `check-inputs.sh` takes
`DISTFILES NEW_WORK` with the builder's tool environment and verifies
rejection of invalid paths, resume inputs and archive checksums.

## Recorded host result

On 2026-10-11, the recipe completed on macOS/arm64 with Apple Clang 21,
CMake 4.4.4, Ninja 1.13.2 and Wayland scanner 1.26.0. Qtbase, ShaderTools,
Declarative and Tools host targets built from the four pinned Qt 6.12.0
archives. The generator and input-rejection checks above passed. The compiled
consumer was Mach-O/arm64; no target executable was run on the host.

The build exposed two reproducibility requirements: separate modules accept
`QT_BUILD_TESTS`/`QT_BUILD_EXAMPLES` CMake settings rather than qtbase's
`-nomake` configure arguments, and Declarative's host targets require the
actual QtTest library even when tests are disabled. Both are in the recipe.

## Target package build

Prepare a new `plasma-mobile` pkgsrc export. Use the existing
[common cross configuration](../../../../profiles/common-build-tools/cross/README.md)
and the fork's verified sysroot. Include the exported common graphics,
common media and Plasma toolkit settings after the cross profile.
Do not include the native-only common tools settings in this cross MAKECONF.
The cross profile identifies the same common tools provider itself.

The graphics, media and toolkit policies preserve native tool recursion:
pkgsrc builds native dependencies with `USE_CROSS_COMPILE=no`. Those builds
must retain the host compiler and prefix. Qt's target Bash dependency is
separate from the executable host Bash tool. Cross job limits come from the
caller's MAKECONF; the toolkit's conservative native default stays unchanged.

The initial qtbase configure uses `QT_HOST_PATH` pointing to the matching
host `qtbase` build directory. Complete target packaging, installed Qt
consumers, plugin discovery and a remote KWin/Plasma session remain gates.
