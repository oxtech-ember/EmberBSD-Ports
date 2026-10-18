# Target std for the shared Rust build host

`lang/rust-std-aarch64-netbsd` adds Rust 1.99 target libraries to the sysroot
owned by the [shared macOS Rust package](rust.md). It is a native host package
containing foreign target data, not a second compiler or a NetBSD rustc package.
It is currently limited to macOS/Apple Silicon and the verified GCC 16.2
NetBSD/AArch64 cross toolchain.

## Source and compatibility

The original `rustc-1.99.1-src.tar.xz` comes from static.rust-lang.org. The
[common source manifest](sources.tsv) pins its SHA256, and the recipe's distinfo
pins BLAKE2s, SHA512, size and patch SHA1. The original Rust licenses are installed.
The only source patch is the existing
[stage0 cross-std integration](../../probes/rust-cross-std/README.md): merge host
sysroot files, omit stale selected cross targets, and install the newly built
std stamp. It is an EmberBSD adaptation with AI assistance, not accepted upstream.
Re-evaluate it when Rust's bootstrap implements this same workflow correctly.

The exact installed official compiler release and commit are checked before
building. Matching the release number alone is insufficient: the tested NetBSD
maintainer's prebuilt std is rejected by this official macOS compiler with
E0514. Its producer version includes a source-tarball suffix. We preserve that
compiler compatibility check; no crate metadata rewriting or consumer
`RUSTC_BOOTSTRAP` override is used.

Upstream x.py builds only stage0 `library`, with local-rebuild, vendored sources,
locked dependencies and offline Cargo. The checked dry-run must not schedule
rustc, LLVM, LLD or a later stage. Existing upstream Python remains a build tool.
Native C/C++ compiler detection and host build-script linking use pkgsrc's host
tools; the target uses explicitly supplied GCC, CRT, sysroot and libgcc.
Debug paths are remapped by upstream bootstrap, and the package checks for work
references. The full target component includes both `.rlib` and `.rmeta` files
and target libstd.so.

## Build and install

Export `common-build-tools` or a composing graphics/media profile. Use the
native macOS MAKECONF and the same host prefix as rust-bin. Keep the work and
package directories outside all input providers. The recipe refuses overlaps,
including the resolved GCC provider behind a tools facade, before extraction.

```sh
MAKECONF=/absolute/native-mk.conf bmake -C /absolute/pkgsrc/lang/rust-std-aarch64-netbsd \
  WRKOBJDIR=/absolute/external/work DISTDIR=/absolute/distfiles \
  PACKAGES=/absolute/external/packages MAKE_JOBS=2 \
  EMBERBSD_RUST_CROSS_TOOLS=/absolute/cross-tools \
  EMBERBSD_RUST_TARGET_SYSROOT=/absolute/target-sysroot package
```

Both cross variables are required. The tools directory supplies
`bin/aarch64--netbsd-{gcc,g++,ar,readelf}`. The sysroot supplies target headers,
base libraries and `/usr/pkg/gcc16` 16.2.0 CRT/runtime. They are build inputs, not
bundled host runtime dependencies. Preserve their revision and file hashes in
the build receipt. Use `install` with the same arguments after package checks.
The exact Rust 1.99 package dependency prevents mixing std with another release.

The native Mach-O shared-library check is inapplicable to this data package.
Its explicit mandatory check instead verifies AArch64 ELF64 libstd, the exact
three NEEDED libraries and target-only RPATH, then checks those three actual
AArch64 sysroot providers. Target libc/libpthread/libgcc are not recorded as
macOS loader requirements. The normal PLIST and work-reference checks remain.
Application packages must still declare and validate their own target runtime
closure; std data is not a deployment bundle.

## Acceptance

```sh
ruby tests/rust-target-paths.rb /absolute/new-path-check
ruby ../../probes/rust-cross-std/test-bootstrap-copy.rb \
  /absolute/patched-rust-source /absolute/host/bin/rustc /absolute/new-copy-check
ruby tests/rust-target-package.rb /absolute/host /absolute/cross-tools \
  /absolute/target-sysroot /absolute/new-consumer-check
```

The first check uses disposable directory fixtures. It rejects overlapping
source/work paths, aliases, a GCC facade and inputs nested inside work. The
second exercises actual upstream copy methods and reproduces the destructive
old-helper failure. The package check verifies registration, file integrity and
ownership of all 53 target files. It uses the installed compiler with no
`--sysroot` override, preserves provider hashes, runs native TLS/unwind, and
links target Rust bin/cdylib and C consumers. An offline Cargo target also runs
a host proc macro and build script; both assert the correct host/target split.

Execute the resulting target consumers using the probe's
[verified target runner](../../probes/rust-cross-std/README.md#checks-and-target-execution).
Run `timeout -k 5 30 /absolute/check/rust-cargo-consumer` on the same target too;
require its `PASS: packaged std with host proc macro and build script` result.
Record the payload and runtime-provider hashes and use no loader overrides.
Link success alone is not target runtime acceptance.

On 2026-10-09, clean package creation and normal installation passed on Apple
Silicon. Package integrity checked all 55 files, including both licenses. The
shared compiler failed with E0463 before installation and linked the same
consumer afterward. Five original host Rust/LLVM providers remained byte-identical.
An isolated NetBSD 11/AArch64 QEMU/HVF VM then passed 32 Rust worker lifecycles,
four C-thread cdylib cycles with nine new TLS destructors each, and the Cargo
consumer. Guest and QEMU exited zero; the root image remained unchanged.
The export passed 70 preflight refusals and exact common-tools composition.

Full current librsvg, GIR/typelib generation, the pixbuf loader and labwc SVG
surfaces are subsequent consumers. This package by itself makes no claim of
an accelerated desktop or physical GPU/NPU support.

## Official x86_64 target data

`lang/rust-std-x86_64-netbsd` installs the official Rust 1.99 component for
`x86_64-unknown-netbsd`. It is native macOS host data for the same shared
`rust-bin` compiler. It installs no target compiler and rebuilds neither
rustc nor LLVM. The source-built AArch64 recipe and its default remain unchanged.

The [official release manifest](https://static.rust-lang.org/dist/channel-rust-1.99.1.toml)
dated 2026-10-15 marks this component available. Its original archive SHA256
is `8eb1d542fe204128ce622c1477bd7e44e1bb041fa30373996a5f24d34184f4aa`.
The downloaded 29,582,788-byte archive matched that TLS-fetched manifest.
Distinfo also pins its BLAKE2s, SHA512 and size. This check is not detached
signature verification. The package retains the upstream licenses and copyright.

Use the native MAKECONF and the shared host prefix:

```sh
MAKECONF=/absolute/native-mk.conf bmake -C /absolute/pkgsrc/lang/rust-std-x86_64-netbsd \
  WRKOBJDIR=/absolute/external/work DISTDIR=/absolute/distfiles \
  PACKAGES=/absolute/external/packages MAKE_JOBS=2 \
  EMBERBSD_RUST_CROSS_TOOLS=/absolute/os-tools package-install
```

The tools prefix supplies host-executable `bin/x86_64--netbsd-readelf`.
No target sysroot is needed to install this host data. The mandatory check
compares all 53 staged component files with the original component manifest
and payload. It checks ELF64/x86_64 identity, the three NEEDED names and the
original `$ORIGIN/../lib` RPATH. It requires the official Rust 1.99 compiler
commit and performs a real target `--emit=metadata` import from the staged
sysroot. E0514 or any other compiler failure stops packaging.

The official libstd retains its original RPATH. It does not select the common
GCC16 runtime by itself. Target consumers must link through the shared GCC16
provider and separately verify their loaded libc, pthread and libgcc closure.
This host data is not a deployment bundle or target runtime acceptance.

The host regression uses the pinned archive and real target readelf:

```sh
ruby tests/rust-target-prebuilt.rb /absolute/x86_64--netbsd-readelf \
  /absolute/rust-std-1.99.1-x86_64-unknown-netbsd.tar.xz /absolute/new-check
```

Nine cases pass for the complete component, damaged/missing/extra data,
foreign ELF, altered providers/RPATH and compiler rejection. The compiler
boundary uses fixtures; it does not establish real metadata acceptance.
Real native bmake variable evaluation passes. Package creation, installed
ownership and real host-compiler metadata acceptance remain pending.

The source-built AArch64 standard library uses a byte-identical temporary
snapshot of package-owned Rust compiler files. This isolates its bootstrap
loader from unrelated libraries in the shared host prefix, including GNU
libiconv. It does not rebuild Rust or change the installed provider. The amd64
recipe continues to use its separately validated official target archive.
