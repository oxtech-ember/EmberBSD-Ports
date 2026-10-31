# Prepare Plasma packages for CM5 acceptance

Build on the development host. The board installs packages and runs tests.
The target is EmberBSD AArch64 with the common Clang/LLVM, Qt6 and Mesa stack.
GCC is an explicit platform alternative where its profile records the reason.
The upstream `NetBSD 11.0` package identifiers describe the compatible ABI.
They do not establish the origin of the installed base system.
The package auditor and installer also accept `--target amd64`, with
`MACHINE_ARCH=x86_64` and ELF machine 62. This requires a separate, coherent
amd64 package closure. Host fixtures do not qualify an amd64 desktop session.

## Complete the package roots

Use the [cross workflow](README.md) and normal pkgsrc package checks.
Prepare these complete roots in the same audited sysroot:

- Plasma Desktop, including its compiled plugins and desktop resources.
- Plasma Workspace, with KWin, KCoreAddons and Xwayland.
- Fcitx Configtool, with the common Fcitx5/Qt6 providers.
- Common Perl for the full-session process supervisor.

Use the current versions and package revisions from the exported common recipes.
The Plasma recipes share the version selected by [plasma6.mk](../../../../pkgsrc/meta-pkgs/kde/plasma6.mk).

Desktop requires the Activities service, not only its client library.
The KActivityManagerD recipe separates its generated package-version header from
upstream's protocol-version header. This fixes an APFS filename collision.
It preserves both the package version and the protocol version.

The KWin recipe exports complete D-Bus property signatures. The native QtDBus
code generators must link the native D-Bus library, as described in
[the actual-generator regression](../tests/kwin-inputdevice-xml.md).
Do not edit the installed XML to repair an incomplete host generator.

Xwayland keeps Glamor, GLX and DRI3. Its common libei 1.6.0nb1 provider keeps
libei, libeis, liboeffis and the target C/C++ test consumers.
The basu 0.2.1nb2 provider uses native Python and gperf for code generation.
It retains registered error maps under LLD section collection and handles
failed POSIX error-string conversion. These repairs belong to the recipes.

The [scoped GCC16/LLD selection](../../../../profiles/common-build-tools/tests/gcc16-lld.md)
sets `/libexec/ld.elf_so` for new executable links when that explicit alternative is used.
Keep its generated specs and compiler/sysroot receipt with that build.
The existing accepted package set also uses `/usr/libexec/ld.elf_so`.
The full-session preflight requires both target paths and creates no aliases.

## Assemble and verify the set

Use [the package-set auditor](../tests/package-set.md) with exact installed
root names. Its input archive list must include the newly built packages.
The auditor resolves actual runtime dependencies and verifies each payload.
It produces a complete local package set and installation order.
It does not extract missing base files from an upstream system image.

Keep the following material in one transfer directory:

- The audited package set, including its manifests and `packages/` directory.
- [The installer](install-package-set.md) and its instructions.
- The complete [Plasma Desktop test directory](../tests/plasma-desktop/README.md).
- The adjacent [full-session test directory](../tests/plasma-session/README.md).
- The [Configtool runtime check](../../../../pkgsrc/inputmethod/fcitx5-configtool/tests/runtime.md).
- The prepared [libei test bundle](../../../../pkgsrc/x11/libei/tests/README.md).
- The prepared [basu local-test bundle](../../../../pkgsrc/devel/basu/tests/target-README.md).
- The [cross-built Qt D-Bus marshalling consumer](../tests/kwin-inputdevice-xml.md#prepare-the-target-consumer).

Copy the full Desktop and session test directories together. Their relative
layout is part of the shared layout-check contract. The libei and basu bundles
already contain target binaries. Their preparation tools do not compile code.
Keep archive SHA256 values, Ports revisions and the base provenance receipt.

Run the installer's `--verify-only` mode on the build host before transfer.
Use native pkgtools for this step. The installer checks every archive before
it starts any package installation. Host checks do not execute target binaries.

## Install and run on the board

Stop any existing Plasma session. Run the installer's explicit `--install`
mode as root with a new log path. Package scripts remain enabled.
Use the existing ordinary desktop account for the acceptance runners.
That account must already have access to the V3D render device.

Run the basu and libei unit bundles first. Then run Configtool, the Desktop
capture check and the full classic session check, each with a new result path.
Keep their output directories. No target compiler or source tree is required.

The Desktop check requires the installed default shell, its panel and applet
models. It records a containment image and actual V3D renderer evidence.
The full-session check uses `startplasma-wayland`, Xwayland, Activities and
KSMServer. It requires stable service owners and a successful normal logout.
Its supervisor bounds the run and cleans only its private marked processes.

These checks use a 1280x1024 virtual output. They do not change an HDMI signal.
Physical display modes still require native BCM2712 KMS acceptance.
Login, physical input, locking, audio, remote desktop and sustained operation
remain separate checks. A complete archive is not a tested desktop session.
