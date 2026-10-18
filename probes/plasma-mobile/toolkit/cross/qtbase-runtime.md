# Qtbase runtime and development packages

NetBSD cross builds for AArch64 and amd64 produce two ordinary source packages:

| Package | Payload and dependency role |
| --- | --- |
| `qt6-qtbase-6.12.0nb2` | Shared libraries, plugins, `qtpaths`, `qtpaths6`, runtime configuration, SBOM and upstream license notices. |
| `qt6-qtbase-devel-6.12.0nb2` | Headers, target generators, static libraries, CMake, pkg-config and other SDK metadata. Requires the exact runtime version. |

The runtime keeps its original package name for normal dependency, update and
vulnerability matching. Revision `nb2` includes the detached-process correction and distinguishes it from the earlier full
package. The SDK conflicts with that earlier package. Native Qtbase keeps its
existing full package and manifest; the separate SDK requires cross mode.

Both recipes use the same pinned archive, patches and source owner. Each performs
an independent full upstream build and installation into its own staging tree.
This costs a second build and avoids a shared build-output handoff.

The complete staging tree passes the existing target metadata normalizer before
selection. Normal pkgsrc expands the full, runtime and SDK manifests with the
selected package options. The partitions must be disjoint and cover every full
manifest entry. Selection rejects missing, unknown, duplicate and unsafe paths
before it removes any unselected file. Selected bytes, modes and symlinks remain
unchanged. Ordinary package checks still apply after selection.

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
ruby tests/qtbase-package-split.rb \
    /absolute/pkgsrc /absolute/native-prefix /absolute/cross-tools \
    /absolute/sysroot /absolute/native-qtbase /absolute/new-split-fixture
ruby tests/qtbase-package-lifecycle.rb \
    /absolute/native-prefix /absolute/new-split-fixture /absolute/new-lifecycle
```

The first check uses real bmake to expand all manifests, inspect dependency roles
and run the actual normalization and stage-selection targets. It supplies explicit
native Clang for the native manifest check and bounds each bmake process group.
Seven invalid-stage cases must fail before pruning. The second check uses native
`pkg_create`, `pkg_add`, `pkg_info` and `pkg_delete` with a private destination and
registry. It replaces the earlier full package, installs and removes the SDK,
enforces the exact dependency and reinstalls runtime alone. Every installed
payload byte and symlink must match the selected staging manifest.

These fixtures contain labelled synthetic text files. They do not compile Qt or
execute target programs. Real Qt cross builds, complete package checks, installed
target replacement/deletion, ELF closure and a real cross CMake consumer remain
required. Historical AArch64 acceptance in [Qt package results](qt-packages.md)
describes the earlier full packages and does not validate these new packages.
