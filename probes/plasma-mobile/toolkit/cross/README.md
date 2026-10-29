# Cross-building the common Qt toolkit

The target is the shared Qt 6.12.0 package set for EmberBSD/AArch64, using
the selected common Clang/LLVM toolchain and current Mesa providers.
The native generator host may be Linux or macOS. A host generator is a build prerequisite, not a second target Qt.
The final target prefix remains `/usr/pkg/qt6`.

## Native generators

The default `QT_HOST_TOOLS_PROFILE=full` uses the seven original Qt archives in [sources.tsv](../sources.tsv): qtbase,
qtsvg, qtshadertools, qtdeclarative, qttools, qtquicktimeline and qtquick3d. The host recipe verifies their
SHA256 before extracting anything. It uses upstream sources with the shared missing-XML null guard;
EmberBSD target portability patches are applied separately by pkgsrc.

Qt requires matching host and target versions. An installed Qt 6.11 toolkit
cannot generate a Qt 6.12 build. See the
[upstream cross-build instructions](https://doc.qt.io/qt-6/cross-compiling-qt.html).

```sh
HOST_SH=/absolute/native/sh CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
TAR=/absolute/native/bsdtar PATCH=/absolute/native/patch \
HOST_PYTHON=/absolute/native/python3 \
WAYLAND_SCANNER=/absolute/wayland-1.26/bin/wayland-scanner \
HOST_LLVM_BUILD=/absolute/native-llvm23 HOST_CLANG_BUILD=/absolute/native-clang23 \
HOST_DBUS_PREFIX=/absolute/native-dbus \
HOST_PACKAGE_PREFIX=/absolute/native-dependencies HOST_PKG_CONFIG=/absolute/native/pkg-config \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ JOBS=4 \
/absolute/native/sh probes/plasma-mobile/toolkit/cross/build-host-tools.sh \
    /absolute/verified-distfiles /absolute/new-host-qt
```

On Darwin, a native stage with libraries outside their installed paths can set
`HOST_RUNTIME_VIEW` to a directory containing the selected runtime libraries and
`HOST_SDK_SOURCE` to the SDK source. The selected native Python runs the SDK
runtime launcher for Qt's custom build commands. The producer records the view
contents. Resume preserves every previous entry and substantial build input. A
view may add a native library only when a previous Qt image or view library
statically declared its absolute dependency and that provider was absent;
selected LLVM inspection rejects shadowed, system and ambiguous providers.
Additions used only through dynamic loading are not supported by this transition.
The previous producer evidence remains in the work directory. Leave these
variables unset for an ordinary installed host runtime.

Set `QT_HOST_TOOLS_PROFILE=quick` for the Core/Quick/QML generator subset.
It uses qtbase, qtsvg, qtshadertools and qtdeclarative. It does not require
qttools, Quick3D, QuickTimeline or the qdoc Clang inputs. The default remains
`full`. `QT_HOST_TOOLS_PLAN_ONLY=1` checks the selected inputs without building.
Select native compilers explicitly; the producer has no system compiler fallback. On macOS set `HOST_MACOSX_DEPLOYMENT_TARGET` to the deployment target selected by the native compiler binding (for example `26.0`). The producer checks that the compiler accepts it, passes it to Qt’s initial CMake configure, and rejects a changed value on resume.
On Darwin, `HOST_CODESIGN` selects the operating system signing service and defaults to `/usr/bin/codesign`; it must be an absolute executable path without shell metacharacters.

`CMAKE` must support Zstandard archives. Qt uses the CMake archive API for its
MIME database. Without this support, Qt stops with `CMake was not built with
zstd support`. The builder checks this before it creates work. The common shared libarchive recipe links Zstandard. Standalone bootstrap
and static bsdtar retain their small compression inputs. Check the installed
CMake API before a Qt build:

```sh
python3 profiles/common-build-tools/tests/cmake-zstd.py \
    --cmake /absolute/native/cmake --work /absolute/new-zstd-check
```

The check creates a Zstandard frame through CMake, extracts it, and compares
the payload. CMake 4.4.4 with libarchive 3.8.10nb3 passed on Linux/amd64.
This archive API result does not establish a Qt generator or target build.

Native QtDBus needs a current D-Bus development prefix at `HOST_DBUS_PREFIX`.
The builder records its headers, library and CMake metadata, then links directly.
This prevents empty complex signatures in KWin's generated D-Bus XML.
See [the generator regression and bounded repair](../tests/kwin-inputdevice-xml.md).

QDoc additionally needs matching LLVM/Clang **23.1.3** libraries and CMake exports
on the host. On macOS/arm64 the verified official SDK can supply both paths;
use [the preparation recipe](../../../../profiles/common-build-tools/cross/prepare-llvm-macos.py)
with the archive named in the common-tools manifest. This native SDK is never
installed in the target sysroot. Its static archives contain LLVM23 LTO bitcode;
the builder selects the matching `libLTO.dylib` for Apple's linker. The older
Apple LLVM21 reader cannot decode those objects.

Set `TMPDIR` and choose `JOBS` from the available host memory and storage.
The recipe keeps per-module configure/build logs, input hashes and tool hashes.
A failed command stops the build. It neither installs target packages nor
reports an accelerated session.

Use `RESUME=1` with the same arguments after correcting a build failure.
The recipe checks the selected tool hashes and all seven archives again,
preserves earlier logs and reuses existing sources and objects. Do not edit
those extracted sources. To reconfigure against an updated selected native
runtime view, set `HOST_INCREMENTAL_RECONFIGURE=1` together with `RESUME=1`.
This records a new input block and permits changed or added runtime providers
only after checking their selected prefixes and existing Mach-O load names;
compiler, ABI, core tools and archived Qt sources remain fixed. Validate the
reconfigured modules and their actual consumers after changing dependencies.

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

Quick 3D additionally needs native `balsam`, the other Quick3D tools and the
Assimp importer plugin. `host_tools` alone produces a `balsam` executable
that rejects real OBJ files. The builder explicitly adds `AssimpImporterPlugin`
and builds the optional Timeline dependency before Quick3D. These private
native libraries do not add another target dependency provider.

Run `cross/check-quick3d-host.sh HOST_QT NEW_WORK` for an actual triangle OBJ
import, nonempty mesh, generated QML bytecode and missing-input check.
The check inspects output files because upstream `balsam` can return exit
status zero even when import fails. This is generator acceptance, not a GPU
rendering result or a working Plasma session.

## Reuse an installed native Qt

An installed Qt 6.12.0 can supply Core, BuildInternals and the usual host tools.
Set `EMBERBSD_QT_HOST_PATH` to its CMake package prefix. Set
`EMBERBSD_QT_HOST_LIBEXECS` to the directory reported by that Qt's
`qtpaths --query QT_INSTALL_LIBEXECS`. The default remains `libexec` below the
host prefix for a Qt build tree. Both native `moc` and the `Qt6CoreTools`
CMake export must exist. Qt's imported targets select the actual tools during
configuration; the target sysroot does not supply them.

Check both a split installation and the default build-tree layout:

```sh
python3 probes/plasma-mobile/toolkit/tests/host-qt-layout.py \
    --bmake /absolute/native/bmake --cmake /absolute/native/cmake \
    --qtpaths /absolute/native/qtpaths --cc /absolute/native/cc \
    --work /absolute/new-host-layout-check
```

The check evaluates the recipe guard, rejects missing tools and metadata,
resolves `Qt6::moc` through installed CMake exports, and executes native `moc`.
It does not compile target code.

If it lacks `Qt6WaylandScannerTools`, build only the missing native scanner:

```sh
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ \
WAYLAND_SCANNER=/absolute/wayland-1.26/bin/wayland-scanner \
sh probes/plasma-mobile/toolkit/cross/build-qtwaylandscanner.sh \
    /absolute/verified-distfiles /absolute/native-qt \
    /absolute/new-scanner-source /absolute/scanner-objects \
    /absolute/new-scanner-prefix
scanner=$(cat /absolute/scanner-objects/installed-scanner-path.txt)
sh probes/plasma-mobile/toolkit/cross/check-qtwaylandscanner.sh \
    "$scanner" /absolute/new-scanner-check
```

The recipe verifies the pinned Qt archive and native versions. It builds the
upstream scanner with the shared Qtbase missing-XML null guard, the installed
Qt build internals and Core.
It preserves the upstream licenses, input hashes and tool logs. Use `RESUME=1`
with the same arguments to verify inputs and reuse its objects. The object
file `installed-scanner-path.txt` records the actual executable path.
The check generates client/server headers and rejects missing or invalid XML.
`check-qtwaylandscanner-inputs.sh DISTFILES HOST_QT NEW_WORK` uses the same
tool environment and rejects unsafe paths, changed inputs, corrupt archives
and interrupted full-host extraction without a patched-source proof.
This bootstrap neither builds target libraries nor disables target Wayland.

With `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY`, CMake can miss native tool
exports in an installed Qt prefix. Pass exact native metadata directories
through `CMAKE_CONFIGURE_ARGS`: `Qt6CoreTools_DIR`, `Qt6GuiTools_DIR`,
`Qt6DBusTools_DIR` and `Qt6WidgetsTools_DIR`. Each value names that host
prefix's `lib/cmake/Qt6<Module>Tools` directory. Set
`Qt6WaylandScannerTools_DIR` to the bootstrap prefix's matching directory.
Keep target package root modes unchanged. Do not select target tool exports.

## Generator acceptance

On Linux or macOS, run the native generator check after building:

```sh
HOST_CC=/absolute/native/cc HOST_CXX=/absolute/native/c++ \
CMAKE=/absolute/native/cmake NINJA=/absolute/native/ninja \
FILE=/absolute/file-inspection-command \
    sh probes/plasma-mobile/toolkit/cross/check-host-tools.sh \
    /absolute/host-qt/qtbase /absolute/new-generator-check
```

Set the same `QT_HOST_TOOLS_PROFILE` used by the producer. The full profile
also checks translations with lrelease. The quick profile omits that qttools
consumer. Both profiles compile and run a real QObject/resource consumer. They compile
UI and QML registration output, generate a shader bundle, QML bytecode
and Wayland headers. The check converts an SVG path to QML, compiles that QML to
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

QDoc was subsequently enabled with the official LLVM/Clang 23.1.3 SDK on
macOS/arm64. `tests/qdoc/run.sh QDOC NEW_OUTPUT` generates class/member HTML
using the actual Clang parser and rejects a missing configuration file.
This host test passes; target QDoc and Qt Assistant remain separate gates.

On 2026-10-12, native Timeline and Quick3D were added from the same pinned
6.12.0 archives. The Assimp importer produces a nonempty triangle mesh and QML;
`qmlcachegen` compiles it, and the missing-input control leaves no output.
The tool hash inventory includes `plugins/assetimporters` as well as executables.
The complete target Quick3D package passes ordinary package checks and CM5
installation; a target Quick3D rendering result is still separate.

## Target package build

Prepare a new pkgsrc export with `scripts/prepare-pkgsrc.py`. Use the existing
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
also passes installed runtime and plugin checks. The [Wayland/EGL V3D check](../tests/qt-wayland-gl/README.md) passes on CM5;
the separate Qt Quick V3D consumer also passes; the complete desktop remains a gate. CM5 desktop acceptance starts with HDMI, then a remote KWin/Plasma session.

## Native tools in consumers

The toolkit profile also passes the selected native `QT_HOST_PATH` to target
CMake consumers. Setting it only in Qt's own recipes leaves KDE packages
unable to use the cross-built Qt. The path expands after profile inclusion,
so existing caller configurations retain their assignment order. Native tool
recursion receives no target Qt host setting.

```sh
BMAKE=/absolute/native/bmake sh \
    probes/plasma-mobile/toolkit/tests/consumer-host-tools.sh \
    /absolute/ports/pkgsrc/plasma-toolkit.mk.conf /absolute/new-consumer-host-test
```

The regression covers assignments before/after inclusion, spaces in paths,
a missing setting and native recursion. It rejects the former profile.
Actual ECM cross configuration exposed the missing host setting. With this
correction and its two new module files retained in PLIST, ECM 6.31.0 passes
ordinary package checks and installation into the common cross sysroot.
Package SHA256: `000fdda5d2329d972852cbcfe51e6eef188a762b93d99d38f469df4af9395441`.
This establishes the build prerequisite, not Frameworks or KWin runtime acceptance.

## Path-only file transfer descriptors

Qt 6.12 cannot compile the desktop portal file-transfer format on EmberBSD
because `O_PATH` is unavailable. The recipe tests
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

Linux/amd64 validation used the quick profile with native Clang 23.1.4.
The fixture compiled and ran; SVG, shader and QML negative cases passed.
This result covers host generators. It does not cover target execution.

## Native Qt Network runtime

Native client development also needs a runnable TLS backend. For an
OpenSSL-enabled Qtbase build, build its existing runtime plugin:

```sh
/absolute/native/cmake --build /absolute/host-qt/qtbase \
    --target QTlsBackendOpenSSLPlugin --parallel 2
/absolute/native/cmake -S probes/plasma-mobile/toolkit/tests/network-runtime \
    -B /absolute/new-network-check -G Ninja \
    -DCMAKE_MAKE_PROGRAM=/absolute/native/ninja \
    -DCMAKE_CXX_COMPILER=/absolute/native/clang++ \
    -DCMAKE_PREFIX_PATH=/absolute/host-qt/qtbase
/absolute/native/cmake --build /absolute/new-network-check
LD_LIBRARY_PATH=/absolute/native/lib /absolute/native/ctest \
    --test-dir /absolute/new-network-check -V
```

The in-process check verifies backend loading and reports its runtime version.
Linux/amd64 Clang 23.1.4 loaded OpenSSL 3.6.5 after the plugin build.
The same fixture failed before the plugin existed. TLS handshakes and target
execution have separate coverage. Host generator checks remain independent.
