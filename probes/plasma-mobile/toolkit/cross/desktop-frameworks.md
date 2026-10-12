# Installed desktop Frameworks and shortcut service

On 2026-10-12, complete KPackage, KIO, Kirigami, KSvg, KGlobalAccel,
KIdleTime and KDeclarative 6.31.0 packages cross-built on macOS for EmberBSD.
KGlobalAccelD 6.7.5 also cross-packaged with the common Qt 6.12 / GCC 16 stack.
The [official stable Plasma index](https://download.kde.org/stable/plasma/)
still lists 6.7.5 as its newest release on this date. Source archive hashes
and original URLs are in [sources.tsv](../sources.tsv).

The normal package checks include manifests, runtime dependencies,
interpreters, permissions, PIE, RELRO, RPATH and build-directory references.
All install into the common sysroot. The first six Frameworks and KGlobalAccelD
also install on CM5; KDeclarative target execution remains pending.
The target dependency batch contains 23 packages; `pkg_admin check` verifies
5,737 installed files. The polkit installation uses pkgsrc's normal
`PKG_CREATE_USERGROUP=yes` mechanism for its non-login service account.
No package checks are disabled and no partial library overlay is installed.

## Cross-build repairs

- ECM defaults to omitting application templates when cross-compiling.
  Enable `KDE_INSTALL_APP_TEMPLATES` in the common Frameworks cross settings.
  Original KIO and Kirigami builds fail manifest checks because their template
  archives are missing; complete packages pass with both archives retained.
- KIO's manifest includes the new rename-warning headers and trash notifier.
  KPackage includes its new Russian manual page. Upstream payload is preserved.
- KGlobalAccelD's library and executable target names differ only in case.
  On the tested build filesystem their CMake object directories resolve to the
  same inode; the original configuration fails during automatic MOC generation.
  Rename only the internal executable target and set `OUTPUT_NAME=kglobalacceld`.
  The installed executable, shared-library ABI and exported target stay unchanged.
  Clean zero-fuzz patch application matches the source used in the successful
  complete build. The patch changes no C++ implementation or input behavior.

## CM5 runtime checks

The board is CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B.
These tests ran after the operator's fan-related kernel update. Each runner
checks that the boot identity is unchanged within its own test interval.
Temporary HOME, runtime and filesystem directories isolate all test data.

Seven unchanged upstream KIO suites pass: metadata, parent URLs, permissions,
protocol discovery, directory-entry serialization, directory creation and deletion.
They report 53 passing rows and two skips. The skips are archive protocols from
uninstalled kio-extras and a permission test which explicitly skips root.
Deletion covers Latin, German and Chinese names, files and directories, plus
cancellation during deletion of a 15,000-file tree. That last suite takes
118 seconds on this board. It is not a filesystem throughput measurement.

Three unchanged upstream KGlobalAccelD suites report 28 passing rows without
skips: configuration migration, shortcuts/contested keys and application
allowlists. They use the upstream dummy input plugin, the installed service
library and private D-Bus sessions. Physical input, compositor delivery and
actual desktop shortcuts are not accepted by this test.

```sh
# Copy the matching upstream _KDE_build/bin executables to EmberBSD,
# verify their hashes, and run with the full packages installed:
sh tests/kio-runtime.sh /absolute/kio-test-binaries /absolute/new-kio-results
sh tests/kglobalacceld-runtime.sh /absolute/shortcut-test-binaries /absolute/new-shortcut-results
```

The scripts live in this toolkit. Each records library resolution, executable
hashes, test exit statuses and boot identity. Upstream tests and expected
results are unchanged. The combined CM5 result archive SHA256 is
`e125f526389e17a4f2ecdc8f54fb9ed88185a6c96b7cfe4c63d232df6e157ed9`.

Cppcheck 2.22 inspected the actual compilation databases: 515 KIO and 23
KGlobalAccelD translation units, with warnings/performance/portability enabled
and a nonzero error exit status. Qt macro and generated-MOC preprocessing
errors prevent clean analysis. Two KIO initialization warnings were inspected:
`LocationInfo` is initialized by aggregate rows, and the owning widget's
constructor sets `m_allTypes` before use. Neither establishes a defect in this
port. No suppressions were added. These changes affect manifests and CMake,
not C++ implementation. Valgrind is unavailable on this target; no memory-safety
certification is claimed.

| Complete package | SHA256 |
| --- | --- |
| kf6-kpackage-6.31.0 | `09f9417825a786adfda6259a32c700c1f9e8477189ff9f014a2805743ce8ee41` |
| kf6-kio-6.31.0 | `bcd68f2205578d94fbba31b642ada1ab3b61a2cd2153e596639988e57c2bc078` |
| kf6-kirigami-6.31.0 | `f4366753c778d59eca77b336f9ed34a81ad21827bc3018d83dcd072bc99e1818` |
| kf6-ksvg-6.31.0 | `4ab866cfe9f7b5122aeba155ee62d0b192de5c685959f3884d937680073ec7de` |
| kf6-kglobalaccel-6.31.0 | `509c056d451be5834d375347dd9898d707a4bb71efb9d5549fcdd23b105ab676` |
| kf6-kidletime-6.31.0 | `eec0533cad20cba69c85ff89af1e16ae3f6069429a6e9c390e4ac42cdc042fd6` |
| plasma6-kglobalacceld-6.7.5 | `b6db4080f99fd60cb89f72d98b87715adaa654fcf940d5f373a5de1ec99ab3bd` |
| kf6-kdeclarative-6.31.0 | `0d755865b97feab3ffa57014af44a077cfd875ce20832b31b2a72c99981fcc40` |

KCMUtils still needs the Sonnet/Aspell/Hunspell dependency chain adapted to
cross compilation. The full KWin package, Plasma login, accelerated desktop,
HDMI and remote-session acceptance remain unfinished. These library checks
must not be presented as a working Plasma session.
