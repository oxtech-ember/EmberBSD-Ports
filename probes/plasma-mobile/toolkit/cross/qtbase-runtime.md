# Qtbase runtime and development packages

NetBSD cross builds for AArch64 and amd64 produce two ordinary source packages:

| Package | Payload and dependency role |
| --- | --- |
| `qt6-qtbase-6.12.0nb2` | Shared libraries, plugins, `qtpaths`, `qtpaths6`, runtime configuration, SBOM and upstream license notices. |
| `qt6-qtbase-devel-6.12.0nb3` | Headers, target generators, static libraries, CMake, pkg-config and other SDK metadata. Requires the exact runtime version. |

The runtime keeps its original package name for normal dependency, update and
vulnerability matching. Revision `nb2` includes the detached-process correction
and distinguishes it from the earlier full package. The SDK conflicts with that
package. SDK `nb3` and native `nb5` fix the XML scanner error path when an input
file cannot be opened. The scanner is not in the runtime payload, so its
revision remains `nb2`. Native Qtbase keeps its full package and manifest.
The separate SDK requires cross mode.

Both recipes use the same pinned archive and source owner. The SDK also includes
the scanner error-path patch. Each performs
an independent full upstream build and installation into its own staging tree.
This costs a second build and avoids a shared build-output handoff.

The complete staging tree passes the existing target metadata normalizer before
selection. Normal pkgsrc expands the full, runtime and SDK manifests with the
selected package options. The partitions must be disjoint and cover every full
manifest entry. Selection rejects missing, unknown, duplicate and unsafe paths
before it removes any unselected file. Selected bytes, modes and symlinks remain
unchanged. Ordinary package checks still apply after selection.

The modern graphics profile requires EGLDevice in both CMake and the manifests.
The contract remains stable before dependency headers or phase caches exist.

The runtime owns license notices, including notices stored below SDK directories.
The exact runtime dependency makes them available with the SDK without duplicate
ownership. Runtime selection does not remove a file because of its directory
alone. A new upstream file requires an explicit manifest classification.

`qt6-qtbase/buildlink3.mk` keeps the runtime as a normal target dependency and adds
the SDK through `BUILDLINK_DEPMETHOD=build`. The development-host sysroot needs both
packages for CMake and header consumers. An execution-only image selects the
runtime. Native generators remain separate host prerequisites. Target `qmake`,
`moc`, `rcc` and `uic` belong to the SDK and must not enter that image.

This split covers Qtbase only. Other Qt packages still require their own payload
audit. For example, `qdbus` belongs to QtTools and has runtime callers. ShaderTools
libraries used by Quick3D must remain even when build-time shader generators move
to an SDK package. This change does not establish a complete runtime-only image.

Interpreter dependency policy is unchanged. The recipes still inherit Python
and bash dependencies associated with SDK scripts. Their exact runtime closure
and helper callers need an audit before changing those dependency roles or
accepting the image closure.

## Source packaging checks

Run these commands from the toolkit directory with real native pkgsrc tools:

```sh
QT_SPLIT_HOST_MAKECONF=/absolute/native-mk.conf \
    /absolute/native-prefix/bin/python3 -B tests/qtbase-package-split.py \
    /absolute/pkgsrc /absolute/native-prefix /absolute/cross-tools \
    /absolute/sysroot /absolute/native-qtbase /absolute/new-split-fixture
/absolute/native-prefix/bin/python3 -B tests/qtbase-package-lifecycle.py \
    /absolute/native-prefix /absolute/new-split-fixture /absolute/new-lifecycle
```

Select the installed prefix make configuration with `QT_SPLIT_HOST_MAKECONF`;
when unset, the first check uses `native-prefix/etc/mk.conf`. The first check uses real bmake to expand all manifests, inspect dependency roles
and run the actual normalization and stage-selection targets. It supplies explicit
native Clang for the native manifest check and bounds each bmake process group.
Seven invalid-stage cases must fail before pruning. The second check uses native
`pkg_create`, `pkg_add`, `pkg_info` and `pkg_delete` with a private destination and
registry. It replaces the earlier full package, installs and removes the SDK,
enforces the exact dependency and reinstalls runtime alone. Every installed
payload byte and symlink must match the selected staging manifest.

These fixtures contain labelled synthetic text files. They do not compile Qt or
execute target programs. The actual AArch64 packages also pass complete upstream
builds, staging, package and ELF checks. The installed cross sysroot passes the
[Core/Gui/SVG CMake consumer](../tests/qt-consumer/README.md).
[Qt package results](qt-packages.md) states the package hashes, installed runtime
acceptance and remaining limits.

## Build and installation

Use the [target package configuration](README.md#target-package-build). Build and
install the runtime before the SDK because the SDK requires its exact version.
Each recipe keeps its full normal build, staging, partition and package checks.
The current hooks use GNU Make for build and installation. Qt's recommendation
to use Ninja does not change that recipe contract.

For a packaging-only change, keep the compiled objects and use separate calls:

```sh
bmake install-clean
bmake repackage
```

Do not combine cleaning and packaging in one bmake call. The global cleaning
mode changes dependency-cookie gating. The normal repackage target also clears
the staging tree before it repeats installation and package checks. Use normal
`replace` for an installed
sysroot update. During a replacement of the earlier full package, its SDK is
unavailable until the separate SDK installation completes. Keep a verified full
rollback package before that update.

Use a public installation umask only for the package process:

```sh
(
    umask 022
    pkg_add -u "$archive"
)
```

A private proof directory can retain umask 077. Do not let that mask reach
`pkg_add`: new public plugin directories must be searchable by ordinary users.
Verify installed payload bytes, modes, symlinks and directory permissions.
