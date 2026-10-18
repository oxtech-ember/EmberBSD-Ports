# Package the GCC16 target runtime

This profile creates `gcc16-runtime-16.2.0nb3` for EmberBSD amd64 or AArch64.
It packages an audited [cross bootstrap stage](../bootstrap/README.md).
All tools execute on the development host. The target receives only shared
libraries and licenses under `/usr/pkg/gcc16` and `/usr/pkg/share/licenses`.
Compiler drivers, headers, CRT objects, static libraries and build tools
remain on the development host.

The explicit [external-compiler bootstrap](../bootstrap/external-compiler.md)
records one existing POSIX GCC16 and a separate generated support snapshot.
Its `runtime-only-external-compiler` marker requires unchanged compiler and
build-plan receipts. The same stage inventory, ELF, dependency, RELRO and
package checks apply. This build mode does not alter package conflicts or
authorize replacing files owned by an installed full `gcc16` package.

The verifier also supports the explicit
[fresh libstdc++ rebuild](../bootstrap/libstdcxx.md) receipt. It checks a frozen
parent snapshot and disjoint component ownership before the same ELF/package
gates. The rebuild must use a new package revision; it cannot replace nb2 under
the same identity. A prepared receipt mode does not establish target acceptance.

The [RELRO relink helper](../bootstrap/relro.md) hardens the three original
runtime DSOs with their authenticated objects and actual upstream link commands.
It reproduces all three baseline DSOs byte-for-byte before adding RELRO.
The AArch64 nb3 package passes normal pkgsrc checks, including RELRO, and
installed SDK and EmberBSD VM checks. Its acceptance is detailed below.
Normal stage verification requires RELRO. Historical provenance reads cannot
install or create packages. No package check is disabled.

The provider conflicts with `gcc16` and `gcc16-libs`. Select one provider
for a coherent package closure. Do not combine the providers or fabricate
a complete `gcc16` package registration. Build consumers with the matching
GCC16 cross compiler and retain their ordinary `/usr/pkg/gcc16/lib` runtime
paths. Do not rename SONAMEs or use an alternate loader search path.

## Why the existing gcc16-libs recipe does not bootstrap this target

The pinned pkgsrc `lang/gcc16-libs/Makefile` has an exact-version
`TOOL_DEPENDS` on the full `gcc16` package. It runs `pkg_info` against that
installed package to discover library files. It then copies those files
under `${LIBGCC_PREFIX}/${GCC_TARGET_MACHINE}`. It cannot consume this
external audited stage and would retain the full-compiler bootstrap cycle.
This package keeps the runtime at `/usr/pkg/gcc16/lib` instead.
The full development package remains available for separate installations.

## Verify the stage

The input is a completed bootstrap work directory, its original GCC archive,
and the exact pkgsrc export used by that build. Keep their recorded paths.
The verifier reads `build-success`, `inputs.txt`, `stage.sha256` and
`stage.symlinks`. It requires exactly one target and its matching triplet,
the exact GCC 16.2.0 archive
SHA256, a full EmberBSD seed commit, and unchanged recipe/patch bytes.
It checks complete stage inventory and every recorded file hash and link.
Missing or additional files, absolute links and escaping links fail.

| Bootstrap target | Exact triplet | Package `MACHINE_ARCH` | ELF `e_machine` |
| --- | --- | --- | --- |
| `amd64` | `x86_64--netbsd` | `x86_64` | 62 |
| `aarch64` | `aarch64--netbsd` | `aarch64` | 183 |

Unknown targets, duplicate target/triplet claims and mismatched triplets fail.
The stage cannot mix architectures, even when every file hash is recorded.

```sh
ruby recipe/files/runtime.rb check /absolute/bootstrap-work \
    /absolute/gcc-16.2.0.tar.xz /absolute/prepared-pkgsrc
```

The default payload consists of `libgcc_s.so.1`, `libstdc++.so.7`, and their
numeric-version targets. A stage explicitly built with `--with-libgomp` and/or
`--with-libatomic` also supplies `libgomp.so.1` and/or `libatomic.so.3`.
These are the pinned GCC source's actual NetBSD SONAMEs; no base or Linux ABI
alias is accepted. The unique `runtime_libraries` input must be the canonical
ordered selection beginning with `libgcc,libstdc++`, optionally followed by
`libgomp` and `libatomic`. A legacy receipt without that field means only the
original pair. Unknown, duplicate, unordered or unterminated selections fail.
Every selected SONAME must exist; an unselected or foreign versioned DSO in
one of these runtime families fails even if recorded in the stage manifest.
The package excludes the unversioned development linker
script and aliases. Each selected file must be a little-endian ELF64
DSO for the selected architecture with the selected SONAME.
The dynamic dependency list accepts only the selected runtimes and the expected
NetBSD base libc, libm and pthread libraries. Runtime search paths may
contain only `/usr/pkg/gcc16/lib`, `/usr/lib` and `/lib`.
The verifier reads ELF headers and dynamic tables directly. It executes
no target file and requires no target `readelf` process.

The source and stage receipts record provenance claims, not signatures.
Their owner must authenticate the seed and source checkout before building.
The packager detects mutations against those receipts. It does not prove
that the recorded source revision was the one used to produce arbitrary bytes.

## Create a package with native host pkgtools

```sh
ruby recipe/files/runtime.rb create /absolute/bootstrap-work \
    /absolute/gcc-16.2.0.tar.xz /absolute/prepared-pkgsrc \
    /absolute/native/pkg_create /absolute/new-package-output
```

The output directory must be new. The packager copies only the selected
payload. It extracts `COPYING3` and `COPYING.RUNTIME` from the verified
original archive. It preserves their original text.
It calls native host `pkg_create` with the installation prefix `/usr/pkg`,
owner `root` and group `wheel`. `+BUILD_INFO` explicitly records
`OPSYS=NetBSD`, `OS_VERSION=11.0` and the selected `MACHINE_ARCH`.
`GCC_RUNTIME_TARGET`, `GCC_RUNTIME_TRIPLET` and `GCC_RUNTIME_MACHINE_ARCH`
record the same verified selection. Package inspection requires each field
exactly once with its original value.
`GCC_RUNTIME_LIBRARIES` and `GCC_RUNTIME_SONAMES` retain the exact library set;
all optional libraries belong to this same provider and conflict policy.
The native host must resolve `root` and `wheel` to UID/GID 0.
On Linux, a process-scoped NSS wrapper can provide the target group mapping.
Do not change package ownership to match a different host group name.
Before creating the output, the packager queries the supplied native
`pkg_create -V`. It requires one eight-digit version line and a valid
calendar date. The package records this queried `PKGTOOLS_VERSION` and
the executable hash in `EMBERBSD_PKG_CREATE_SHA256`. The pkgsrc package
revision, such as `nb1`, is not part of the pkgtools version.
The executable hash must remain unchanged through package creation.
It also records source, recipe and stage SHA256 values, the seed commit,
the GCC version and the selected SONAME.
The resulting archive is inspected again for payload, unchanged bytes,
links, conflicts, prefix and unique target/package-tool metadata.
Stage verification runs again against the original stage-only result.
Package-tool provenance does not replace or modify the stage receipts.

Successful output contains the package, `package.sha256` and
`provenance.json`. A failed attempt removes only its new output directory.
Input stages, compiler outputs, source archives and pkgsrc stay unchanged.
Temporary package and audit directories are removed after the operation.

## Ordinary pkgsrc integration

The `recipe/` directory is an overlay for `lang/gcc16-runtime`.
Exporting it belongs to the profile composition workflow.
The recipe performs no compilation. It uses the same verifier and produces
a generated PLIST from the audited stage. Supply these build-host variables:

```text
GCC16_RUNTIME_RUBY=/absolute/native/ruby
GCC16_RUNTIME_WORK=/absolute/bootstrap-work
GCC16_RUNTIME_ARCHIVE=/absolute/gcc-16.2.0.tar.xz
GCC16_RUNTIME_PKGSRC=/absolute/prepared-pkgsrc
```

Use the common cross configuration for the selected target, target metadata,
DESTDIR and native package tools. The recipe must not install Ruby or a
compiler on the target. Its `BUILD_DEFS` retain the same provenance fields.
The recipe rejects a stage whose architecture differs from pkgsrc's
`MACHINE_ARCH`. The stage selection never overrides the package target.
The direct packager above also works on macOS without running target pkgtools.

## Checks and acceptance boundary

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_ADD=/absolute/native/pkg_add \
    ruby tests/package-test.rb
```

The fixtures test both architectures, SONAME, old C++ dependencies, source/recipe
mutations, incomplete inventory, link escapes, omitted intermediate aliases,
conflicting target/triplet claims and output reuse. An AArch64 fixture
reproduces the former rejection of every target except amd64.
Mixed ELF architectures and uniformly wrong ELF architectures fail in
both directions, including with updated stage hash receipts.
Optional-library checks cover each selection, missing payload, incorrect
SONAMEs, mixed architectures, unshipped intermediate aliases, second ABI
copies, and dependencies on unselected runtimes. Both default and extended
synthetic-ELF packages are created/installed for each architecture with real
native pkgtools when available.
With `PKG_CREATE`, they create
and inspect a real package using synthetic target ELF files and license data.
With `PKG_ADD`, they install it into a private destination using normal
`-I -K /usr/pkg/pkgdb -P DEST -m 'NetBSD/ARCH 11.0'` options, where
`ARCH` is `x86_64` or `aarch64` from the selected fixture.
They also recreate the previous missing-version warning and require the
corrected package to install without that warning. Invalid version queries,
calendar dates and changes to the queried executable fail before stage access.
They do not compile GCC and are not target runtime acceptance.
Without that variable, the native-package fixture is explicitly skipped.

Set `BMAKE` and `PKGSRC` to enable real pkgsrc recipe parsing.
Also set `GCC_ARCHIVE` to the pinned original archive to check the recipe's
architecture guard through the real source verifier. This case retains
synthetic stage DSOs. It accepts matching `MACHINE_ARCH` and rejects the
opposite architecture for both targets.

The current host suite passes 16 tests and 555 assertions with zero failures,
errors or skips. It uses real native pkgtools, bmake, pkgsrc and the pinned
GCC archive. Four synthetic-ELF packages cover both architectures and both
library selections. Refusal checks also cover missing RELRO, changed inherited
components, unowned relink changes and relative receipt input paths.

These synthetic fixtures do not qualify a real runtime or installed consumer.
Before release, build the actual stage and package from a clean
Ports commit. Install, remove and reinstall with target pkgtools in an
EmberBSD VM of the selected architecture. Run prebuilt C11/C++20 threads, TLS, DSO exception and
object-exchange consumers. Confirm the loaded runtime hashes and one
libstdc++/libgcc_s provider per process. An extended stage also needs actual
OpenMP parallel-work and atomic-operation consumers with its selected library
hashes. Repeat relevant Plasma acceptance.
No compiler or target-side build is required for these runtime checks.

## AArch64 installed acceptance

The accepted AArch64 package is `gcc16-runtime-16.2.0nb3`, prepared with the
runtime recipe and RELRO helper at Ports commit
`42925ebde42d1389f10f65d126988ce392e9390d`. Normal pkgsrc packaging passes
all standard checks, including RELRO and runtime paths. Its SHA256 is
`c6db6c55a44c8aa5de89b6569dddbd4d04bb164447b8af6b891be40ee6467335`.

The fresh libstdc++ build includes the [locale repair](../locale.md) and
retains all 6,190 defined dynamic symbol identities. The three other DSOs
use authenticated original objects and upstream link commands. Each original
link reproduces its accepted baseline byte-for-byte; adding `-Wl,-z,relro`
preserves symbol identities and sizes, SONAMEs and dependencies.

Normal SDK package replacement verifies all nine runtime payload entries.
The matching 881-entry libstdc++ development stage is synchronized separately.
Only `bits/c++locale.h` and four static archives change in that development
update. All 26 support entries outside its ownership remain unchanged,
including their modification times; the GCC16 prefix retains 912 entries.
The SDK keeps the unversioned linker files, OpenMP headers and specs required
by fresh cross-built consumers.

The AArch64 QEMU guest used the fork's `EMBER64` kernel and verified E34
development sets from OS commit `6dd57144183678938164b4c2dcfc370cdbde8473`.
The [E34 workflow](https://github.com/oxtech-ember/EmberBSD/actions/runs/38843939746)
supplied the base, comp and matching compressed kernel. Their SHA256 values are:

| Input | SHA256 |
| --- | --- |
| `base.tar.xz` | `688dc6701cd83283d1287fc18dee8b9af35f067096cdd4a92de7e0593fdacddb` |
| `comp.tar.xz` | `8c813303f0500ae1a4ba6381eee6a1189ffab86036963fb26f36ec313e02daa6` |
| `netbsd-EMBER64.gz` | `fbc6fa0afe2a91e7798734f58a326d18ccb20bb46e20b1f3579359264e68ea90` |

Target `pkg_add -U` upgrades the installed provider to nb3. All nine payload
entries match their package hashes or links, and package integrity passes.
Fresh GCC16 consumers use the installed SDK header and ordinary runtime paths.
C11/C++20 thread, TLS, atomic and floating-point constant-evaluation checks
pass in plain and LTO builds. DSO object exchange and exception unwinding
also pass. Numeric conversions and stream semantics pass with two workers
and an independent ambient-locale observer, without a private conversion
object. Both numeric conversion builds, plain and LTO, pass.

The [OpenMP contract](../tests/libgomp.md) passes reductions, locked tasks
and worker TLS with four workers in plain and LTO builds. The atomic contract
passes 256-byte load/store/exchange and 2,000 concurrent compare/exchange updates
in both builds. Both OpenMP negative controls return the expected status 1
and diagnostic. The [Skia contract](../../common-graphics/cross/wxwebkit.md#netbsd-numeric-locale)
also passes after rebuilding its 13 selected units against the new header.
It uses genuine `fr_FR.UTF-8` locale data.

Actual loaded providers matched these installed package hashes:

| Provider under `/usr/pkg/gcc16/lib` | SHA256 |
| --- | --- |
| `libgcc_s.so.1` | `e518f14d51dfca1157caba79ccc5a8c59c370a93ee039f387e3770a4360246fa` |
| `libstdc++.so.7` | `ece362b9af59cb3d744a1d67e8a7dcd54b58c94f9ee6cee10f39545891288965` |
| `libgomp.so.1` | `905b183142c69999210a2b5d458f8586530196c6e4b95c2678accdfb3caec276` |
| `libatomic.so.3` | `3947e466cd5cd409f149699057369bd7405c202dc0c4e35ad4bb859ed5f3d2a8` |

No loader override or target compiler is used. This acceptance covers the
normal nb3 upgrade and these installed consumers. Removal and reinstallation
were checked for nb2; they have not been repeated for nb3. Complete the nb3
lifecycle check before release. This does not qualify amd64 execution,
KiCad, Plasma, a complete image or physical hardware.
