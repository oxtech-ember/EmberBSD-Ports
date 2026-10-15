# Cross-build the CSS parser bridge

This recipe uses the shared Rust 1.99.0 build-host provider and the selected
GCC16 target wrappers. It accepts only NetBSD 11 targets with matching pkgsrc,
Rust and GNU identifiers:

| pkgsrc architecture | Rust target | GNU target |
| --- | --- | --- |
| aarch64 | aarch64-unknown-netbsd | aarch64--netbsd |
| x86_64 | x86_64-unknown-netbsd | x86_64--netbsd |

The cross profile supplies `CROSS_MACHINE_ARCH` and the native C/C++ compiler
paths. Cargo's target linker and the C++ bridge use the same target wrappers.
Host build scripts and proc macros keep the native compilers. The native Cargo
linker key comes from the actual `rustc -vV` host triple, so an amd64 target
does not imply an amd64 build host. Native dependency recursion receives no
cross Cargo configuration from this recipe.

## Prepare the shared Rust provider

Use a native host MAKECONF with the same host prefix as
`EMBERBSD_CROSS_HOST_PREFIX`. Keep normal package checks enabled. The
[common Rust provider](../../../../../../profiles/common-build-tools/rust.md)
owns the checked original host archive and Darwin package adaptation.

```sh
/absolute/host/bin/bmake -C /absolute/pkgsrc/lang/rust-bin \
    MAKECONF=/absolute/native.mk.conf \
    WRKOBJDIR=/absolute/host-work DISTDIR=/absolute/distfiles \
    PACKAGES=/absolute/host-packages CHECK_SHLIBS=yes package
```

Install that accepted host package with native pkgtools or the same recipe's
normal `install` target. Do not install a target compiler into the VM.

For amd64, build/install `lang/rust-std-x86_64-netbsd` with that same native
MAKECONF and host prefix. It contains the official matching target data in
`lib/rustlib/x86_64-unknown-netbsd/lib`; it does not add another compiler.
Supply its required cross inspection tools:

```sh
/absolute/host/bin/bmake -C /absolute/pkgsrc/lang/rust-std-x86_64-netbsd \
    MAKECONF=/absolute/native.mk.conf \
    WRKOBJDIR=/absolute/host-work DISTDIR=/absolute/distfiles \
    PACKAGES=/absolute/host-packages \
    EMBERBSD_RUST_CROSS_TOOLS=/absolute/cross-tools package
```

Keep that provider's manifest, compiler identity and ELF checks enabled, then
use its normal `install` target. AArch64 keeps the existing
`lang/rust-std-aarch64-netbsd` source-built data package and its separate
[cross tools/sysroot inputs](../../../../../../profiles/common-build-tools/rust-target-std.md).
Do not substitute a same-version std built by an incompatible compiler.

## Configure and build the consumer

Build this recipe with the normal common tools, graphics/media and Plasma
cross MAKECONF. Its native tool dependencies select the shared `rust-bin`
and architecture-specific std data package. Cargo uses the pinned vendored
crate closure with `--offline`; no target tool runs on the host.

Before Cargo, `files/verify-cross-inputs.sh` checks the official compiler
release and commit, matching Cargo, both GCC16 wrapper triples, and the std
location inside the shared host prefix. It requires std/core `.rlib` files.
It then compiles a small real Rust consumer to target **metadata only**.
This makes the compiler enforce producer/target compatibility, including
E0514, without a linker or target execution. The resulting
`WRKDIR/target-std-check.rmeta` remains build evidence.

Missing std, a mixed architecture or incompatible compiler metadata is a
failure. The recipe does not rewrite crate metadata or use `RUSTC_BOOTSTRAP`.
The target VM only installs and tests the resulting shared parser library.
It receives neither this host Rust provider nor development tools.

## Host checks

```sh
BMAKE=/absolute/host/bin/bmake ruby tests/cross-targets.rb
sh tests/inputs.sh
```

The make fixture evaluates the production cross settings for both targets,
native recursion and foreign/mixed inputs. The shell fixture supplies explicit
compiler-response boundaries to check ordering, std refusal and dynamic host
identification. These checks do not build the parser or prove real std, Cargo,
Qt/Union, package lifecycle or target runtime acceptance. Those remain required
with the normally installed providers and the actual source archives.
