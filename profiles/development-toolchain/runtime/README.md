# Package the GCC16 target runtime

This profile creates `gcc16-runtime-16.2.0nb3` for EmberBSD amd64 or AArch64.
It packages an audited [cross bootstrap stage](../bootstrap/README.md).
All tools execute on the development host. The target receives only shared
libraries and licenses under `/usr/pkg/gcc16` and `/usr/pkg/share/licenses`.
Compiler drivers, headers, CRT objects, static libraries and build tools
remain on the development host.

The verifier also supports the explicit
[fresh libstdc++ rebuild](../bootstrap/libstdcxx.md) receipt. It checks a frozen
parent snapshot and disjoint component ownership before the same ELF/package
gates. The rebuild must use a new package revision; it cannot replace nb2 under
the same identity. A prepared receipt mode does not establish target acceptance.

The [RELRO relink helper](../bootstrap/relro.md) hardens the three original
runtime DSOs with their authenticated objects and actual upstream link commands.
It reproduces all three baseline DSOs byte-for-byte before adding RELRO.
The AArch64 link, ABI and stock pkgsrc RELRO checks pass. The new nb3 package
and target runtime still need their ordinary acceptance checks.
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

The earlier architecture-only host suite passed 9 tests and 209 assertions
with all five tool/source variables, native pkgtools 20260227 and bmake
20240909. The extended suite additionally packages optional runtimes; its
synthetic ELF files do not execute any target code or establish runtime
acceptance.
On 2026-10-18 the extended suite passed 11 tests and 431 assertions with no
skips using those native tools and the pinned GCC archive. Four synthetic-ELF
packages (default and extended, both architectures) were created, inspected
and installed into private host destinations. The real completed AArch64
bootstrap also passed the extension's read-only preflight without modifying
its stage. Actual optional-library installation and target execution were
not part of these checks.

An earlier completed amd64 runtime stage was also repackaged and
installed with native pkgtools 20260227 into an isolated host destination.
The old package reproduced `lacks pkg_install version data`.
The new package installed without warnings; its DSO bytes, aliases and target
metadata matched the original stage. This is host packaging evidence.
The accepted target runtime artifact and shared package databases were unchanged.

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

On 2026-10-18, a real extended stage and nb2 package passed read-only inventory,
ELF, package creation and isolated host installation checks. The optional
runtime extension used Ports commit `28510febf8194b9fb3f89f6b5f7a3d7ac411d430`.
The application compiler used the cross recipe at commit
`0635104994dd2e7b57c9f4c3158516f9c75e9b04` and native GCC 16.2.0.
The runtime package SHA256 is
`a1e274027ef6fc8183e0f373890a7080fe4c3176be2a45b4512695303dad1e54`.

The AArch64 QEMU guest used the fork's `EMBER64` kernel and verified E34
development sets from OS commit `6dd57144183678938164b4c2dcfc370cdbde8473`.
The [E34 workflow](https://github.com/oxtech-ember/EmberBSD/actions/runs/38843939746)
supplied the base, comp and matching compressed kernel. Their SHA256 values are:

| Input | SHA256 |
| --- | --- |
| `base.tar.xz` | `688dc6701cd83283d1287fc18dee8b9af35f067096cdd4a92de7e0593fdacddb` |
| `comp.tar.xz` | `8c813303f0500ae1a4ba6381eee6a1189ffab86036963fb26f36ec313e02daa6` |
| `netbsd-EMBER64.gz` | `fbc6fa0afe2a91e7798734f58a326d18ccb20bb46e20b1f3579359264e68ea90` |

Target pkgtools installed and checked all nine package entries. Prebuilt
C11 and C++20 tests passed plain/LTO compilation, threads, TLS, atomics,
floating-point constant evaluation, DSO object exchange and exception unwinding.
The [OpenMP contract](../tests/libgomp.md) passed reductions, locked tasks
and worker TLS with four workers. The separate atomic contract passed
256-byte load/store/exchange and 2,000 concurrent compare/exchange updates.
Both OpenMP negative controls rejected the invalid inputs.

Actual loaded providers matched these installed package hashes:

| Provider under `/usr/pkg/gcc16/lib` | SHA256 |
| --- | --- |
| `libgcc_s.so.1` | `71c89f59a0b1d9d96f94d07303d0727e60addcfc5ad4533c024dea331d4d93f5` |
| `libstdc++.so.7` | `b9b90b7d765eabacbe01c00a16fbb9846f0e3bfd4c56955599843e062173bf5c` |
| `libgomp.so.1` | `b3718586235d5689b1d3339e0f2b64b8a1f8cb5a4e330cefd8947ec6d648dd19` |
| `libatomic.so.3` | `10685292d1cc2e2558ffcb5b349329114c5102143c07cc07ff106cb799c26dce` |

Package removal made the consumers fail at the loader for the absent DSOs.
Reinstallation restored all functional results and package integrity checks.
No loader override or target compiler was used. This qualifies this AArch64
runtime package and these consumers. It does not qualify amd64 execution,
KiCad, Plasma, a complete image or physical hardware.
