# LXQt 2.4 on the common Qt6 profile

The target is [LXQt 2.4.0](https://lxqt-project.org/release/2026/04/20/release-lxqt-2-4-0/),
released on 20 April 2026. The pinned pkgsrc already supplies this release,
including panel 2.4.1, PCManFM-Qt 2.4.1 and Wayland session 0.4.1.
This probe retains one common GCC16, Qt 6.12 and KDE Frameworks 6.31 stack.

## Source and package ownership

The recipes under `recipes/` derive from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Original RCS identifiers,
licenses, source checksums, manifests and portability patches are retained.
The local adaptation separates native generators from target libraries.
It retains the target plugin paths and fixes the backlight helper defects
described below.
It is AI-assisted EmberBSD work and has not been submitted upstream.

Copy the recipe overlay into a prepared `plasma-mobile` pkgsrc export.
Include the common cross, graphics, media and toolkit profiles in that order.
Use the shared EmberBSD sysroot and GCC16 toolchain.
Build ordinary packages with `bmake package`.
Install dependencies with ordinary package tools before building consumers.

## Native generators

LXQt CMake and translation modules need matching host Qt tools.
They do not require another target Qt or another native Qt library build.
Prepare these modules from the verified original archive:

```sh
python3 probes/lxqt/build-host-tools.py \
    /absolute/distfiles/lxqt-build-tools-2.4.0.tar.xz \
    /absolute/common-host-qt /absolute/new-lxqt-host-work \
    --cmake /absolute/cmake --ninja /absolute/ninja
```

Set `EMBERBSD_LXQT_HOST_TOOLS` to the printed staged prefix.
Set `EMBERBSD_QT_HOST_PATH` to the existing matching native Qt prefix.
The cross recipes select its `Qt6LinguistTools` export explicitly.
The generated LXQt configuration retains the target `/usr/pkg` paths.
Native pkgsrc builds retain their original `TOOL_DEPENDS` behavior.

libqtxdg also selects the target icon-engine directory explicitly. A native
`qtpaths --query QT_INSTALL_PLUGINS` returns the host path during cross builds.
The ordinary target package must retain `/usr/pkg/qt6/plugins/iconengines`.
Its upstream tests are compiled with `BUILD_TESTS=ON`; execution remains separate.
The directory tests use the same package prefix as `xdgdirs.cpp`.

The current LayerShellQt package exports `LayerShellQt::Interface`.
The leave dialog uses this target and requires LayerShellQt 6.8.

The helper verifies the original archive before extraction and refuses an
existing output directory. It preserves configure, build and install logs.
On macOS/arm64 it passes with the common Qt 6.12 host tools.

The terminal closure retains xterm 412 and current luit 20260907. xterm needs
the native `tbl` generator to prepare its complete manual. Use an existing
current groff `tbl`, or prepare it from the common source and patches:

```sh
python3 probes/lxqt/build-tbl.py /absolute/distfiles/groff-1.24.2.tar.gz \
    /absolute/new-native-tbl-work --make /absolute/gmake
```

Set `TOOLS_PLATFORM.tbl` to the printed executable. This builds the original
upstream generator and all its required generated headers. It does not change
the target groff options or install another target provider.

The native cross-libtool recipe keeps compiler selection in the consumer's
wrapper `PATH`. This lets pkgsrc map buildlink paths during shared linking.
Both compiler tags and `LTCC` retain the selected GCC16 tool names.
The causal libXpm rebuild passes the ordinary RPATH and work-directory checks.

## Source regressions

The liblxqt backlight helper checks the driver before reading its files.
It accepts one integer from `scanf` and `fscanf` and rejects invalid input.
It releases a previous driver candidate before replacing that candidate.
The driver priority and valid brightness range are unchanged.

Run the regression against a clean original liblxqt archive and the same
source with `patch-backlight-null-driver` applied:

```sh
python3 probes/lxqt/check-backlight.py /absolute/original-liblxqt \
    /absolute/new-baseline-results --baseline
python3 probes/lxqt/check-backlight.py /absolute/patched-liblxqt \
    /absolute/new-port-results
```

The test includes the real source. It uses synthetic files and checks missing
devices, replaced allocation ownership, malformed input and valid boundaries.
It does not access a backlight device. The native run uses ASan and UBSan.
An explicit allocation counter checks the replaced driver strings because
LeakSanitizer is unavailable on the macOS/arm64 host.

Baseline and patched Cppcheck runs use the GCC16 target headers and macros.
The helper's null-driver finding and two GCC `-fanalyzer` ownership findings
are absent after the patch. Clang Static Analyzer checks both the C helper
and its C++ consumer with the target compilation flags. It is analysis-only.
The existing style findings remain visible.

The luit recipe declares zlib and the existing common encodings package.
It selects target `locale.alias` and `encodings.dir` paths explicitly.
The configure patch preserves native file checks. In cross mode, the recipe
checks these files in the common sysroot before configuration.

```sh
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-luit-results
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-target-results \
    --ssh ember-test-host
```

All six upstream check modes and two exact-byte encoding conversions pass
with the GCC16 target binary. The same eight cases pass in a native
ASan/UBSan build. Valgrind Memcheck does not support the tested macOS/arm64
host or EmberBSD/aarch64 guest. These sanitizer runs are not Memcheck runs.

## Acceptance boundary

The common GCC16 build compiles libqtxdg 4.4.0, liblxqt 2.4.0,
qtxdg-tools 4.4.0 and lxqt-session 2.4.0. The three real libqtxdg test
programs pass 21 cases on an unprivileged EmberBSD/aarch64 VM with the
offscreen Qt platform plugin. This component run uses an application runtime
bundle from the same common sysroot. It does not establish package installation
or a desktop session.

Prepared host modules are a build prerequisite. Compilation and component
tests do not establish power control, input or rendering.
X11 and Wayland session execution require separate target acceptance.
The Wayland session requires a supported compositor and its own package.
