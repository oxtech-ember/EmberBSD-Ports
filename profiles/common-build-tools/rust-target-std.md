# Target std for the shared Rust build host

`lang/rust-std-x86_64-netbsd` and `lang/rust-std-aarch64-netbsd` provide
foreign target data for the shared Rust 1.99.1 host compiler. They do not
install a second compiler or rebuild rustc or LLVM. Both default to the shared
Clang/LLVM target toolchain and the selected target sysroot. The producer runs
upstream x.py only for stage0 `library`, with vendored dependencies and offline
Cargo. It checks that the plan does not schedule a compiler or LLVM rebuild.

The source and checksums are in the recipes and [source manifest](sources.tsv).
The common patches preserve stage0 cross-std integration and select `libunwind`
on NetBSD only when the upstream `system-llvm-libunwind` feature is active;
the existing default `libgcc_s` selection remains available. On Apple hosts the
bootstrap shim uses `DYLD_FALLBACK_LIBRARY_PATH`, preserving absolute system
library install names while locating the selected Rust shared libraries. These
are EmberBSD adaptations with AI assistance, not accepted upstream.

## LLVM build

Export the common recipes, select the native MAKECONF, and build the package
for the target. The SDK source, installed native compiler prefix, target sysroot,
macOS SDK, deployment target, shared lock root and heavy-link context are
explicit inputs. The sysroot must contain the selected LLVM runtime. For example:

```sh
MAKECONF=/absolute/native-mk.conf bmake -C /absolute/pkgsrc/lang/rust-std-x86_64-netbsd \
  WRKOBJDIR=/absolute/work DISTDIR=/absolute/distfiles PACKAGES=/absolute/packages \
  EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
  EMBERBSD_RUST_COMPILER_PREFIX=/absolute/host-prefix \
  EMBERBSD_RUST_TARGET_SYSROOT=/absolute/target-sysroot \
  EMBERBSD_RUST_MACOS_SDK=/absolute/MacOSX.sdk EMBERBSD_RUST_MACOS_MINIMUM=26.0 \
  EMBERBSD_RUST_LOCK_ROOT=/absolute/shared-object-root \
  EMBERBSD_RUST_LINK_CONTEXT=/absolute/shared-object-root/coordination/heavy-link \
  EMBERBSD_RUST_BUILD_JOBS=4 package
```

The common producer selects native and target compiler bindings separately,
checks the host compiler and Rust version, and routes both host and target links
through the SDK link launcher. The build checks its target libstd and a real
static-std consumer linked with the selected target compiler; both must depend
on LLVM libunwind and not libgcc_s. It does not execute target code or establish
application runtime compatibility. Normal package checks and the exact Rust
package dependency still apply.

`pkgsrc/lang/rust-bin/files/target-std/test-unwind.py` exercises the actual
NetBSD link declarations with and without the system feature. The adjacent
`test-make-selection.py` checks target and explicit family selection, and
`test-bootstrap-loader.py` checks the patched host loader choice and runs the
selected host rustc. The full source build additionally exercises the actual
bootstrap shim and target link.

A source-built x86_64 std and a static Rust consumer were cross-linked using
Clang/LLVM and verified for LLVM libunwind on a Darwin arm64 host. Target
execution and the source-built LLVM AArch64 package require their own checks.

## Explicit GCC alternative

The existing AArch64 GCC producer remains available only when the platform
chooses `EMBERBSD_RUST_TARGET_COMPILER_FAMILY=gcc` and supplies
`EMBERBSD_RUST_GCC_REASON`, `EMBERBSD_RUST_CROSS_TOOLS`, and the matching target
sysroot. It is limited to Darwin arm64 hosts and retains its GCC runtime checks.
It previously passed package, consumer and NetBSD AArch64 VM checks; those do
not establish acceptance of the LLVM producer or a physical GPU.

The older official x86_64 target component links against `libgcc_s` even for a
static-std consumer. Keep its package for rollback where needed; it is not
compatible with the selected LLVM-only runtime merely because metadata loads.
