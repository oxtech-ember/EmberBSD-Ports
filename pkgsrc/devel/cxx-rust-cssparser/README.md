# Cross-build the CSS parser bridge

This recipe uses the shared Rust 1.99.1 build-host provider and the selected
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
[common Rust provider](../../../profiles/common-build-tools/rust.md)
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
[cross tools/sysroot inputs](../../../profiles/common-build-tools/rust-target-std.md).
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

## Reproduce the derived vendor source

The previous `cxx-rust-cssparser-vendor-1.1.0.tar.gz` source entry pointed to a
GitHub Cargo.lock HTML page. It was not a vendor archive. The recipe now uses
the locally derived plain USTAR `cxx-rust-cssparser-vendor-1.1.0-r1.tar`.
It does not advertise a replacement upstream HTTP asset.

`files/vendor.rb` prepares the replacement on the build host using Ruby 3.1
or newer, RubyGems and the shared official native Rust/Cargo 1.99.1 provider.
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
closure and output hashes with input, helper and output hashes.

The original lock supplies 61 crates. Complete original file audits retain
103 license/notice files and 36 restored VCS metadata files.
[vendor-r1.json](files/vendor-r1.json) records the derivation inputs and
hashes. It is a host derivation receipt, not an upstream release signature.

The resulting archive is 40,816,640 bytes. Its SHA256 is
`d2e42517a49923fcd79fb7f05b650a4821c218c4d04d9c9691c7fdef55e74a2a`.
The recipe and toolkit manifest now select that exact file and keep normal
BLAKE2s, SHA512 and size checks. The validator permits
`derived:cssparser-vendor-r1` only for this owner, filename and hash, bound to
the unchanged original source archive and declared primary. Other derived
markers and plain TAR filenames fail.

After reproducing and comparing both generations, copy the verified archive
into `DISTDIR` and verify the copied bytes. `pre-fetch` refuses a missing or
changed derived archive with generation instructions. The original GitHub
source still uses normal framework fetch and checksum handling. No checksum,
patch, ownership or payload verification is skipped.

Real native `cargo metadata --offline --locked --filter-platform
x86_64-unknown-netbsd` also resolves from the archive-extracted vendor tree
with an empty private Cargo home. Its selected graph contains 52 registry
packages plus the local root. The full source vendor closure remains 61.
This does not compile the parser or accept a target package/runtime. The
application cross build, target dependency closure and binary-package notice
acceptance still require their own checks.

## Installed notices and license metadata

The recipe's normal `post-install` target installs all 103 original registry
license and notice files under `share/licenses/cxx-rust-cssparser/vendor`.
This covers all 61 source crates, including crates outside the filtered
amd64 graph. It is a source notice superset, not a list of linked objects.
The package also retains all five original project license texts,
`REUSE.toml`, `Cargo.lock`, the derivation receipt and the notice hash manifest.
Normal PLIST entries own every installed file.

`files/notices.sha256` pins every original notice path and SHA256.
`files/install-notices.sh` uses the supplied native pkgsrc digest tool.
It verifies the complete manifest before creating the destination.
Missing or changed files, symlinks, unsafe paths and duplicate entries fail.
The recipe supplies its normal `INSTALL_DATA`, `DESTDIR` and `PREFIX`.
No target executable or additional language interpreter runs for installation.

`files/licenses.json` records the original SPDX expressions and manifest
hashes for the 52 registry packages in the actual amd64 Cargo metadata graph.
It preserves upstream project attribution and explains the pkgsrc mappings.
The recipe combines component requirements with `AND`; each component's
alternative licenses keep `OR`. The library's original headers permit
`LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL`.
The package selects the permitted LGPL 2.1 branch and retains all original
alternative license texts. `BSD-2-Clause` maps to `2-clause-bsd`.
`Unicode-3.0` maps to the existing pkgsrc `unicode-v3` identifier.
The legacy `MIT/Apache-2.0` declaration in siphasher is an alternative;
its original `COPYING` explicitly permits either license.

The amd64 Rust std provider retains its own original licenses and
`COPYRIGHT`. A host data provider is not automatically a runtime package.
The Rust `staticlib` can embed std objects. The real compiler and link outputs
must establish linked std and third-party scope before binary acceptance.
The filtered source graph and notice installation check do not prove that scope.

Run the notice regression with the original extracted project source,
the fully audited vendor directory, the native pkgsrc digest executable,
and the pinned pkgsrc license directory:

```sh
ruby tests/notices.rb /absolute/original-source /absolute/verified-vendor \
    /absolute/host/bin/digest /absolute/pkgsrc/licenses
```

It compares actual source notices and SPDX declarations, installs into a
private fixture, and rejects missing, changed or unsafe inputs.
The separate native pkgsrc `post-install` check uses the exported recipe
and a private package destination. These are host installation contracts;
target compilation, binary package and VM acceptance remain pending.

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
