# Rust 1.99 target standard library on a macOS build host

This source probe builds the NetBSD/AArch64 standard library with the official
Rust 1.99.1 Apple Silicon compiler and the existing GCC 16.2.0 cross toolchain.
It provides the compiler/runtime compatibility check needed before building
current librsvg for the common Wayland desktop. It is not an installed Rust,
librsvg or desktop package.

## Why build std separately?

The checksum-verified NetBSD maintainer's Rust 1.99 binary distribution could
not supply std to the official macOS compiler: a metadata compile returned
E0514 despite the same reported release and source commit. Matching filenames
and versions are insufficient to establish compiler metadata compatibility.
We do not rewrite metadata or enable unstable flags in application builds.

Upstream bootstrap supports a stage0 cross-library build with `local-rebuild`.
In this configuration, its `StdLink` step copied the initial sysroot instead
of installing the newly compiled target artifacts. The
[patch](patches/stage0-cross-std.patch) installs that build's stamp and excludes
initial components for the selected cross targets. It merges the rest of the
initial sysroot without deleting already built targets, native objects or
host files. Normal non-local-rebuild behavior is unchanged.

The patch is an EmberBSD adaptation with AI assistance; it has not been
submitted or accepted upstream. Re-evaluate it when updating Rust. Remove it
when upstream's unmodified stage0 path passes the same contracts.

The compiler retains its private upstream LLVM 23.1.1 backend. This probe
neither rebuilds rustc/LLVM nor replaces the target's shared LLVM 23.1.2
provider used by Mesa. NetBSD unwind links to the existing GCC16 runtime.

## Inputs and build

[sources.tsv](sources.tsv) pins original URLs and SHA256 values. Verify archives
before extracting. Use the three official host components (rustc, cargo and
host std) in one isolated host prefix; their upstream `install.sh` accepts
`--prefix=ABS_HOST_RUST --disable-ldconfig`. Do not install a NetBSD compiler
on macOS. Keep the complete upstream licences and component manifests.

Required inputs:

- Apple Silicon macOS, Ruby, native build tools and upstream bootstrap's
  existing Python dependency; tested with Python 3.14.
- Official Rust 1.99.1, commit `58cf8f9c35b355199727627d07ae34a4e2846d67`,
  and matching native cargo/host std.
- The [GCC16 cross toolchain](../../profiles/development-toolchain/cross/README.md)
  and a NetBSD/AArch64 sysroot containing its actual headers, CRT objects,
  libc, libpthread and `/usr/pkg/gcc16/lib/libgcc_s.so.1`.
- The full verified `rustc-1.99.1-src.tar.xz`, which includes bootstrap and
  vendored crates. The smaller rust-src component is insufficient.
- A new absolute work directory outside all inputs, with at least 8 GiB free.

```sh
PYTHON=/absolute/path/to/python3 ruby build.rb \
  /absolute/host-rust /absolute/cross-tools /absolute/target-sysroot \
  /absolute/downloads/rustc-1.99.1-src.tar.xz /absolute/new-work
```

The helper uses two jobs and offline vendored Cargo dependencies. It checks
the dry-run plan before the real stage0 library build. Logs and generated
configuration remain in the work directory. A source tarball can cause an
upstream `git: not a repository` diagnostic; the actual bootstrap exit status
still determines success.

The output component is
`out/aarch64-apple-darwin/stage0-sysroot/lib/rustlib/aarch64-unknown-netbsd`.
Rust 1.99 emits separate `.rmeta` files: keep the entire component, not only
its `.rlib` files. The helper also links the executable, Rust cdylib and C
consumer under `runtime/`. Their RPATH selects `/usr/pkg/gcc16/lib`; no build
sysroot path belongs in installed ELF metadata.

## Checks and target execution

[test-bootstrap-copy.rb](test-bootstrap-copy.rb) extracts the actual production
copy methods into a native filesystem harness. It checks preservation of two
cross targets, a self-contained native object and host-only files; omission of
stale selected components; immutable inputs; and dry-run behavior. The previous
filtered-copy method must reproduce the destructive-copy failure.

[runtime.rs](runtime.rs) checks allocation, a libc call, 32 joined Rust threads,
TLS isolation/destructors and caught unwinding. [consumer.c](consumer.c) starts
a C thread before each of four `dlopen` calls. Each call creates eight Rust
workers; after joining the original C thread, the test requires nine new TLS
destructors before `dlclose`. It measures the counter's delta because the loader
may retain a DSO after closing its handle. This is bounded lifecycle coverage, not a general
stress test or proof that unloading arbitrary Rust libraries is safe.

Stage all three target binaries in an isolated NetBSD/AArch64 VM using its
normal libc, libpthread, loader and installed GCC16 runtime. Copy
[run-on-target.sh](run-on-target.sh) alongside them. Supply a trusted
`files.sha256` with SHA256 and absolute guest path for all three binaries,
the runner, `libgcc_s.so.1`, libc, libpthread and the physical loader file.
Do not hash an absolute guest symlink by following it on the build host.
Run from the guest with writable `/tmp`:

```sh
sh /tests/rust/run-on-target.sh /tests/rust
```

The runner rejects library-path/preload overrides, checks hashes before and
after execution, checks that Rust resolves the canonical GCC16 library, and
bounds each consumer to 30 seconds plus five seconds for termination. Keep
the guest output, QEMU status, kernel/image hashes and immutable root-image
hash with the build receipt. Host execution alone does not validate NetBSD.

The old pkgsrc workaround disabling AArch64 compiler TLS cites
[NetBSD PR 58154](https://gnats.netbsd.org/58154), closed after fixes to HEAD and
the NetBSD 9/10 branches. This probe retains the official compiler's TLS
behavior and checks it on the actual NetBSD 11 runtime. It does not establish
support for older loaders or every dynamically loaded TLS configuration.

## Boundary

On 2026-10-08 the patched stage0 build, production copy regression and native
control passed on Apple Silicon macOS. The cross-built executable and cdylib
passed the contracts above in an isolated NetBSD 11/AArch64 QEMU/HVF guest
with the existing GCC16 runtime. Each C-thread cycle recorded nine new TLS
destructors. Incomplete and duplicate manifests were rejected before consumer
execution. Target and QEMU exit statuses were zero; the root image and all
provider hashes were unchanged. This is software-runtime VM acceptance.

The [shared Rust/cargo-c provider](../../profiles/common-build-tools/rust.md)
and [target std package](../../profiles/common-build-tools/rust-target-std.md)
now pass normal host installation and target consumers. This probe remains
the source/bootstrap regression. librsvg's complete SVG/GIR/pixbuf package
and real labwc client/input/VT acceptance remain separate steps. See the
[desktop dependency boundary](../../profiles/common-graphics/cross/labwc-dependencies.md).
