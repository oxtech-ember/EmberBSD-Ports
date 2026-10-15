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
ruby tests/vendor.rb
```

The make fixture evaluates the production cross settings for both targets,
native recursion and foreign/mixed inputs. The shell fixture supplies explicit
compiler-response boundaries to check ordering, std refusal and dynamic host
identification. These checks do not build the parser or prove real std, Cargo,
Qt/Union, package lifecycle or target runtime acceptance. Those remain required
with the normally installed providers and the actual source archives.

## Reproduce the missing vendor source

The old `cxx-rust-cssparser-vendor-1.1.0.tar.gz` source entry points to a
GitHub Cargo.lock HTML page, which is not a vendor archive. No published
upstream release asset has been established for that entry. Do not manufacture
bytes to match its old digest or disable source verification.

`files/vendor.rb` prepares the replacement on the build host using Ruby 3.1
or newer, RubyGems and the shared official native Rust/Cargo 1.99.0 provider.
It does not compile Rust or require target std. Its original upstream archive
and Cargo.lock hashes are pinned; `files/vendor-crates.tsv` records the exact
61 registry crate identities and checksums from that lock. It rejects any
other dependency source. A fresh work directory gives Cargo a fresh private
cache; no existing vendor tree or Cargo configuration is imported.

The hash-pinned GitHub source archive contains one global PAX header named
`pax_global_header`, with exactly the commit comment for
`d7bd0b6a6ca1db88a8189aee81498f194f1e45a5`. The helper accepts only that exact
header type, name and payload after verifying the original archive hash.
It preserves those bytes in `source-metadata.json` and the final receipt.
Other PAX metadata, including path/link directives, fails; no PAX directives
are interpreted during extraction.

```sh
ruby files/vendor.rb \
    /absolute/distfiles/cxx-rust-cssparser-1.1.0.tar.gz \
    /absolute/host /absolute/vendor-r1-first
ruby files/vendor.rb \
    /absolute/distfiles/cxx-rust-cssparser-1.1.0.tar.gz \
    /absolute/host /absolute/vendor-r1-second
cmp /absolute/vendor-r1-first/cxx-rust-cssparser-vendor-1.1.0-r1.tar \
    /absolute/vendor-r1-second/cxx-rust-cssparser-vendor-1.1.0-r1.tar
```

Cargo runs `vendor --locked --versioned-dirs` against the checked original
manifest. The helper checks every cached `.crate` against Cargo.lock and
requires the vendor file set and bytes to match both that original archive
and Cargo's `.cargo-checksum.json`. Original license/notice files are retained
and counted in the receipt. Symlinks, special files and extra crates fail.
Cargo omits `.gitignore` and `.gitattributes`, including nested copies.
The helper restores only missing files with those exact basenames from each
already checksum-verified original `.crate`. It records each restored path,
file hash and archive hash, and updates the local Cargo checksum map.
Existing changed files are rejected, not replaced. The final complete archive,
file-byte, license and checksum audit remains mandatory without omissions.

The result is plain USTAR, using the standard RubyGems writer with
`SOURCE_DATE_EPOCH=0`, sorted names, uid/gid zero, `wheel` owner/group and
0755 directory modes. Regular files use 0644 or 0755 according to their
executable bit. The helper checks the writer's metadata contract; the archive
has no compression-version dependency. `receipt.json` records input, helper,
closure and output hashes plus actual provider and Ruby identities.

The helper and its synthetic host fixture alone do not establish the derived
artifact hash. Until two real native Cargo runs produce identical bytes,
the replacement filename is intentionally not wired into DISTFILES, distinfo
or the toolkit source manifest. The follow-up must record the actual SHA256,
normal pkgsrc BLAKE2s/SHA512/size, and the narrowly scoped derived-source
provenance rule before exporting or building this recipe on a fresh host.

To include the actual pinned source extraction in the host regression, run:

```sh
CSSPARSER_UPSTREAM_ARCHIVE=/absolute/distfiles/cxx-rust-cssparser-1.1.0.tar.gz \
    ruby tests/vendor.rb
```

This invokes the production CLI with controlled provider-response fixtures,
checks the extracted original lock and preserved PAX comment, then requires
the controlled Cargo boundary to fail before any vendor artifact is published.
It proves source extraction and rejection behavior only; it does not run or
accept native Cargo, registry downloads, or a complete derived vendor archive.
