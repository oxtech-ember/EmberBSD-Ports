# Cross-building the common Qt toolkit

The target is the shared Qt 6.12.0 package set for EmberBSD/AArch64, using
GCC 16.2 and the current common Mesa/LLVM providers. The build host may be
macOS. A host generator is a build prerequisite, not a second target Qt.
The final target prefix remains `/usr/pkg/qt6`.

## Native generators

Use the five original Qt archives in [sources.tsv](../sources.tsv): qtbase,
qtsvg, qtshadertools, qtdeclarative and qttools. The host recipe verifies their
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
The recipe checks the selected tool hashes and all five archives again,
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

Target Quick VectorImage also requires the native `svgtoqml` generator and
its Qt6QuickTools CMake export. Build host SVG before Declarative and explicitly
enable Quick VectorImage; otherwise cross configuration fails even though
the earlier host_tools build succeeded. The minimal host QPA plugin lets the
generator check run without a window server. The target feature stays enabled.

## Generator acceptance

On macOS, run the native generator check after building:

```sh
HOST_CXX=/absolute/native/c++ sh \
    probes/plasma-mobile/toolkit/cross/check-host-tools.sh \
    /absolute/host-qt/qtbase /absolute/new-generator-check
```

It compiles and runs a real QObject/resource/translation consumer, compiles
UI and QML registration output, generates a shader bundle, QML bytecode
and Wayland headers. It converts an SVG path to QML, compiles that QML to
bytecode, and rejects missing SVG and invalid shader/QML inputs. It does not
run a GUI or establish target Qt compatibility. `check-inputs.sh` takes
`DISTFILES NEW_WORK` with the builder's tool environment and verifies
rejection of invalid paths, resume inputs and archive checksums.

## Recorded host result

On 2026-10-11, the recipe completed on macOS/arm64 with Apple Clang 21,
CMake 4.4.4, Ninja 1.13.2 and Wayland scanner 1.26.0. Qtbase, SVG, ShaderTools,
Declarative and Tools host targets built from the five pinned Qt 6.12.0
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

Set `EMBERBSD_QT_HOST_PATH` to the matching host `qtbase` build directory and
`EMBERBSD_WAYLAND_SCANNER` to the native scanner. The shared Qt recipe passes
these paths to CMake, retains the target tools required by the package and
requires the Wayland client/EGL features on supported targets. A missing
scanner must not silently produce a desktop package without Wayland.

The recipe also roots pkg-config output in the target sysroot during configure
and build regeneration. Compiler wrappers alone cannot repair imported CMake
include paths: CMake validates those paths before it invokes the compiler.
The EGLDevice package manifest checks the selected Mesa header inside the
sysroot when cross-compiling.

On 2026-10-11, actual Qtbase configuration on macOS/GCC16 passed with EGL,
GBM, EGLDevice and Wayland client/EGL enabled. Native generators executed on
the host. Reproduce the configuration check after running pkgsrc configure:

```sh
sh probes/plasma-mobile/toolkit/cross/check-target-configure.sh \
    /absolute/target-qt-build /absolute/host-qt/qtbase \
    /absolute/sysroot /absolute/native/wayland-scanner
```

This check examines the real CMake cache and executes the selected host tools.
[Qtbase, SVG, ShaderTools, ImageFormats and LanguageServer packaging](qt-packages.md) now passes, including
ordinary sysroot installation. The [CM5 Core/Gui/SVG consumer](../tests/qt-consumer/README.md)
also passes installed runtime and plugin checks. Quick and accelerated Qt remain
gates. CM5 desktop acceptance starts with HDMI, then a remote KWin/Plasma session.

## Path-only file transfer descriptors

Qt 6.12 initially enabled the desktop portal file-transfer format on EmberBSD,
then failed to compile because `O_PATH` is unavailable. The recipe now tests
this API with the target compiler before enabling that feature. Substituting
`O_RDONLY` would change file permissions and directory semantics and could
block on a FIFO. See the upstream [FileTransfer contract](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.FileTransfer.html).
Normal Wayland MIME/URI transfer, clipboard, drag-and-drop and D-Bus remain enabled.
This does not implement Flatpak document sharing on EmberBSD.

`tests/portal-feature.sh QT_SOURCE NEW_WORK` evaluates the patched Qt feature
condition for all 32 prerequisite combinations. On 2026-10-11 it rejected the
original condition and passed the port. The pinned archive hash, both configure
patch hashes, zero-fuzz application and exact live build source comparison passed.
The real GCC16 cross configuration has the portal format off and the existing
Wayland/EGL/GBM features on; `check-target-configure.sh` verifies these together.
When continuing an old build, remove only that feature's stale CMake cache entry
with CMake's `-U` option before reconfiguration; do not delete the object tree.
Qtbase compilation and packaging pass with this correction. The installed
Core/Gui/SVG check now passes; portal behavior and the full desktop remain
separate acceptance gates.
