# LXQt 2.4 on the common Qt6 profile

The target is [LXQt 2.4.0](https://lxqt-project.org/release/2026/04/20/release-lxqt-2-4-0/),
released on 20 April 2026. The pinned pkgsrc already supplies this release,
including panel 2.4.1, PCManFM-Qt 2.4.1 and Wayland session 0.4.1.
This probe retains one common GCC16, Qt 6.12 and KDE Frameworks 6.31 stack.

## Source and package ownership

The recipes under `recipes/` derive from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. Original RCS identifiers,
licenses, source checksums, manifests and portability patches are retained.
The local adaptation only separates native generators from target libraries.
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

## Acceptance boundary

Prepared host modules are a build prerequisite. They do not establish
target libraries, an installed session, power control, input or rendering.
X11 and Wayland session execution require separate target acceptance.
The Wayland session requires a supported compositor and its own package.
