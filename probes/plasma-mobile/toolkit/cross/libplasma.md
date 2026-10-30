# libplasma cross package and CM5 acceptance

Complete libplasma and PlasmaActivities 6.7.5 packages build on macOS with
GCC 16.2, common Qt 6.12.0 and Frameworks 6.31.0. They install into the common
EmberBSD sysroot and pass focused installed-library checks on CM5.
The full accelerated KWin/Plasma session remains unaccepted.

## Package metadata consistency

The previously tested 6.8.0 recipe used SONAME 8 for libPlasma and libPlasmaQuick.
That nb1 package revision rebuilt metadata with the complete current PLIST.
A stale `+BUILD_INFO` can still advertise SONAME 7 and require its own
SONAME 8 libraries. `pkg_add` checks those requirements before extraction.
Regenerate metadata through the normal pkgsrc package target; do not remove
requirements by hand or bypass the shared-library check. The
[package-set auditor](../tests/package-set.md) rejects this mismatch before transfer.
These metadata checks do not establish the new package's hardware behavior.

## Native package metadata tool

libplasma's configure step imports KPackage's native tool. Build the actual
KPackage 6.31 generator and its private host libraries from pinned archives:

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja \
HOST_CC=/absolute/cc HOST_CXX=/absolute/c++ JOBS=2 \
EXTRA_HOST_PREFIX=/absolute/native-gettext \
  sh build-kpackage-tool.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR \
    HOST_DOCTOOLS NEW_WORK
```

`HOST_DOCTOOLS` is the matching [native KDocTools prefix](doctools.md), which
already provides KArchive. Copy `NEW_WORK/tooling/KF6Package` into the common
`EMBERBSD_KF6_HOST_TOOLING` directory. The imported executable is global, so
sibling CMake directories resolve it. The host libraries stay private;
all target KPackage components remain installed. Upstream's CLI reports
version `2.0`; the helper checks the real Frameworks version header, `6.31.0`.
The upstream build still needs Python for translations; no new Python helper
is introduced here.

`tests/kpackage-metadata.sh` checks five upstream JSON fixtures, stdout/file
output, NoDisplay omission and missing-input rejection. Four upstream expected
XML files were stale: they used `developer_name`, omitted the homepage, or
named authors absent from their input JSON. The recipe corrects those expected
files only. All five cases pass with both the native tool and the installed
CM5 executable. Production metadata generation remains upstream code.

## Preserve EGL and application templates

With the common non-GLVND Mesa, ECM finds `EGL::EGL`, but CMake does not expose
`OpenGL::EGL`. libplasma previously ignored the successful fallback discovery
and compiled with `HAVE_EGL=0`. The patch selects the actual available target
and links the window-thumbnail implementation to it. The GLVND case retains
its original target; a genuinely missing EGL provider stays unavailable.

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja PKG_CONFIG=/absolute/pkg-config \
  ruby ../tests/libplasma-egl.rb LIBPLASMA_SOURCE CROSS_TOOLS SYSROOT NEW_WORK
```

This regression executes the production CMake selection and link blocks with
the actual common Mesa sysroot. The original source fails because it loses
EGL; the patched source passes and links an AArch64 ELF module to `libEGL`.
The complete package configures with `HAVE_EGL=1`. It also retains all four
application templates: cross builds now explicitly enable
`KDE_INSTALL_APP_TEMPLATES`, matching the Frameworks provider policy.

## Bounded hardware result

On 2026-10-12, CM5 Rev 1.0 / BCM2712 D0 / 4 GiB / Waveshare CM5-NANO-B passes:

- `pluginloadertest`: 4 passes, including a real static containment-action
  plugin and installed package structure discovery;
- `themetest`: 4 passes, including theme configuration and exact colors;
  one X11 compositing case is skipped by upstream on the offscreen platform;
- `sharedqmlenginetest`: 5 passes, including shared-engine identity and final
  ownership release.

Run the actual upstream ELF binaries with `tests/libplasma-runtime.sh`, placing
`bin/` and the unchanged `autotests/data` directory in its input bundle.
The script uses private HOME/XDG state, a private D-Bus session and finite
process deadlines. These tests use offscreen software rendering. They do not
prove GPU-rendered thumbnails, interactive shell windows or a full desktop.
Package payloads match the common sysroot: 363 libplasma files and 29
PlasmaActivities files, including links. Installed package checks pass;
the CM5 fan kernel and boot time remain unchanged.

| Package | SHA256 |
| --- | --- |
| plasma6-libplasma-6.7.5 | `ea63096b3dddaf4569349948d3b0432cc71d51b1de1936a479d228352feb60b2` |
| plasma6-plasma-activities-6.7.5 | `d175a7a01e0b7b6a4e2e6e0f180581404260be1df3881fbcc25cc583f27aefb3` |

Cppcheck 2.22 was run against the actual native KPackage CLI compilation
commands. It stops on Qt declaration macros; this is not a clean source audit.
Valgrind is unavailable. The production C++ code in these packages is unchanged;
the functional libplasma adaptation is in its CMake provider selection.

The original archive URLs and SHA256 are in [sources.tsv](../sources.tsv).
Recipe origins are pinned pkgsrc; adaptation ownership is EmberBSD Ports.
These AI-assisted changes have not been submitted or accepted upstream.
