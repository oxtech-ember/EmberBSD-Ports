# Shared Rollup 4.65.1

This recipe owns the native Rollup parser used by host build tools. It combines
upstream's JavaScript distribution with a parser compiled from the matching
Rust source; it does not install a downloaded `.node` binary or run npm install.
The [4.65.1 release](https://github.com/rollup/rollup/releases/tag/v4.65.1) corresponds
to Git commit `7879c65994dd591d287b177b8d0b88d7d76c2a49`. Both archives and the
195 Cargo registry inputs are pinned in `distinfo`; crate SHA256 values retain
Cargo.lock's independent integrity checks.

The JS distribution includes its complete upstream LICENSE.md. Its runtime
`@types/estree` dependency is the shared `devel/node-types-estree` 1.0.9 package;
Node uses the current shared Node 24 LTS recipe. Optional npm native binaries
are not installed. The N-API module is installed locally under the filename
already supported by upstream's native loader. A small recipe patch adds
NetBSD arm64/x64 mappings while retaining the loader's diagnostics.

## Build inputs and allocator policy

The recipe includes the [shared Cargo owner](../../../profiles/common-build-tools/cargo.md).
Rust/Cargo and Python are native tools. C/C++/AR commands, flags, package target,
output directory and offline vendor sources are selected explicitly. Native
Darwin and NetBSD/FreeBSD/Linux arm64/x64 metadata defaults are supplied; other
upstream platforms may set `EMBER_CARGO_TARGET` and `ROLLUP_NAPI_BASE` explicitly.
A cross build also needs the matching target Rust std component and target SDK.
These configuration inputs do not establish target execution support.

`libmimalloc-sys2` declares Cargo's `links = "mimalloc_sys2"`. The recipe supplies
a standard target build-script override to link the common
[mimalloc 3.6.0 provider](../mimalloc/README.md). Cargo must skip the bundled
native allocator builder. The Rust dependency explicitly enables its `v3`
feature while retaining upstream's existing platform features and global
allocator. No private mimalloc C builder or copy of its portability patches is
maintained here.

The selected mimalloc package must have `malloc-override` disabled. For a native
Darwin configuration, select it explicitly in MAKECONF:

```make
PKG_OPTIONS.mimalloc= -malloc-override
```

ELF addon configurations require `dynamic-tls`; non-Apple AArch64 also requires
`generic-arch`, preserving Rollup's baseline CPU requirement. For that case:

```make
PKG_OPTIONS.mimalloc= -malloc-override dynamic-tls generic-arch
```

Changing allocator configuration requires rebuilding that shared provider and
incompatible consumers. An already installed package with unsuitable options
is rejected at configure; source fetch/checksum remain independent. In
particular, the pinned C++ Mold 2.42.1 consumer requires override mode and is not
accepted with the same embedding artifact. This recipe does not migrate Mold.

Use normal pkgsrc commands with the selected native or cross MAKECONF:

```sh
bmake -C /absolute/pkgsrc/devel/rollup fetch checksum
bmake -C /absolute/pkgsrc/devel/rollup package
bmake -C /absolute/pkgsrc/devel/rollup test
```

Build dependencies must be installed by the ordinary package graph before
configuration. Native generator packages are built with the native profile;
a target compiler does not produce a runnable host parser. Target package
execution and native host execution remain distinct checks.

## Notices

The package preserves all 279 original LICENSE/LICENCE/COPYING/NOTICE/AUTHORS
files supplied by its 195 crate archives, together with their exact Cargo
package and available VCS metadata. `share/licenses/rollup/index.json` records
original SPDX expressions, authors, archive SHA256 and copied notice hashes.
The recipe's LICENSE expression covers the closure, including Apache, Unicode,
Boost, BSD, ISC and zlib code in addition to MIT.

Thirty-four upstream crate archives do not contain standalone notice files.
Nine of them receive original notices restored from their exact recorded VCS
commits (napi-rs, SIMD and ddbase). The recipe checks those Git blob hashes and
crate commit identities; origins remain in the installed index. For the rest,
the package preserves the supplied metadata and README where present, and
records an empty original-notices list. Standard license texts
are included separately; they are not invented upstream copyright notices.
Some SWC VCS refs supplied in the archives no longer resolve through GitHub.
The recipe keeps the checked archive inputs and does not substitute current
Git content for those pins. LLVM exceptions and other additional permissions
remain in the original notice files where supplied.

## Source and native checks

```sh
python3 -B -I -S pkgsrc/devel/rollup/tests/source.py
python3 -B -I -S pkgsrc/devel/rollup/tests/source.py \
  --distdir /absolute/distfiles --patch /absolute/declared/patch \
  --license-root /absolute/pkgsrc/licenses --work /absolute/new-source-check
python3 -B -I -S pkgsrc/devel/rollup/tests/pkgsrc-source.py \
  --pkgsrc /absolute/completed-pkgsrc --bmake /absolute/native/bin/bmake \
  --makeconf /absolute/native-mk.conf --shell /absolute/native/bin/mksh \
  --distdir /absolute/distfiles
python3 -B -I -S pkgsrc/devel/rollup/tests/native-loader.py \
  --node /absolute/native/bin/node \
  --source /absolute/patched-rollup/npm/package/dist/native.js \
  --archive /absolute/distfiles/rollup-4.65.1.tgz
```

The tests cover thirteen input/notice cases, all 197 actual distfiles, 195 Cargo.lock
checksums, both patches with no fuzz or offsets, and preservation of original
allocator feature policies. Sixteen real pkgsrc checks cover source phases,
native/cross metadata and ESTree's five-file data installation. No downloaded
Rust or N-API binary is used as build evidence; the source-only mimalloc input
is an explicitly empty fixture library. The native-loader check executes both
the exact upstream and patched JavaScript with platform/addon fixtures: NetBSD
arm64/x64 mappings, missing/corrupt addon diagnostics, and seven existing
platform mappings. It does not execute a NetBSD binary.

The native `test` target exercises the built N-API binding:
synchronous and concurrent asynchronous parsing, hashing, module bundling,
syntax-error propagation and a corrupt-addon dlopen control. It uses selected
Node and a separate temporary module copy. Cross `test` refuses to execute
target Node on the host. These functional checks pass on Darwin arm64 with
source-built Rust and N-API code, the selected Clang/LLD and shared mimalloc.
They are separate from memory instrumentation and target runtime checks.

The Chromium and DevTools consumers still need an explicit binding to this
provider; this recipe alone does not remove their existing private providers.
Target Rust std availability, target compilation and target execution remain
unverified.

`tests/mimalloc-cargo.py` exercises the actual pinned `mimalloc-safe` and
`libmimalloc-sys2` crates with the recipe-generated standard Cargo override and
an ordinary shared mimalloc 3.6.0 embedding library. The selected native Rust
allocator executes allocation, ownership and cross-thread free checks,
while ordinary C malloc remains with the process allocator. A deliberately
unavailable CMake proves the bundled allocator build script is skipped; removing
only the override must fail in that script. Crate sources remain unchanged.
The current execution covers Darwin arm64 and is separate from the full Rollup
N-API addon and target runtime checks. Supply the prepared source/vendor, staged
shared library and selected SDK/native inputs documented by `--help`.
