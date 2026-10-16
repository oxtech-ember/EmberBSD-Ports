# Package the GCC16 target runtime

This profile creates `gcc16-runtime-16.2.0nb1` for EmberBSD amd64.
It packages an audited [cross bootstrap stage](../bootstrap/README.md).
All tools execute on the development host. The target receives only shared
libraries and licenses under `/usr/pkg/gcc16` and `/usr/pkg/share/licenses`.
Compiler drivers, headers, CRT objects, static libraries and build tools
remain on the development host.

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
`stage.symlinks`. It requires the amd64 target, the exact GCC 16.2.0 archive
SHA256, a full EmberBSD seed commit, and unchanged recipe/patch bytes.
It checks complete stage inventory and every recorded file hash and link.
Missing or additional files, absolute links and escaping links fail.

```sh
ruby recipe/files/runtime.rb check /absolute/bootstrap-work \
    /absolute/gcc-16.2.0.tar.xz /absolute/prepared-pkgsrc
```

The payload consists of `libgcc_s.so.1`, `libstdc++.so.7`, and their
numeric-version targets. It excludes the unversioned development linker
script and aliases. Each selected file must be a little-endian ELF64
x86_64 DSO. Its SONAME must be `libgcc_s.so.1` or `libstdc++.so.7`.
The dynamic dependency list accepts only these runtimes and the expected
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
`OPSYS=NetBSD`, `OS_VERSION=11.0` and `MACHINE_ARCH=x86_64`.
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

Use the common cross configuration for the amd64 target, target metadata,
DESTDIR and native package tools. The recipe must not install Ruby or a
compiler on the target. Its `BUILD_DEFS` retain the same provenance fields.
The direct packager above also works on macOS without running target pkgtools.

## Checks and acceptance boundary

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_ADD=/absolute/native/pkg_add \
    ruby tests/package-test.rb
```

The fixtures test architecture, SONAME, old C++ dependencies, source/recipe
mutations, incomplete inventory, link escapes, omitted intermediate aliases,
conflicting target claims and output reuse. With `PKG_CREATE`, they create
and inspect a real package using synthetic target ELF files and license data.
With `PKG_ADD`, they install it into a private destination using normal
`-I -K /usr/pkg/pkgdb -P DEST -m 'NetBSD/x86_64 11.0'` options.
They also recreate the previous missing-version warning and require the
corrected package to install without that warning. Invalid version queries,
calendar dates and changes to the queried executable fail before stage access.
They do not compile GCC and are not target runtime acceptance.
Without that variable, the native-package fixture is explicitly skipped.

The actual completed amd64 runtime stage has also been repackaged and
installed with native pkgtools 20260227 into an isolated host destination.
The old package reproduced `lacks pkg_install version data`.
The new package installed without warnings; its DSO bytes, aliases and target
metadata matched the original stage. This is host packaging evidence.
The accepted target runtime artifact and shared package databases were unchanged.

No real amd64 runtime package or installed consumer is qualified by these
fixtures. Before release, build the actual stage and package from a clean
Ports commit. Install, remove and reinstall with target pkgtools in an
EmberBSD amd64 VM. Run prebuilt C11/C++20 threads, TLS, DSO exception and
object-exchange consumers. Confirm the loaded runtime hashes and one
libstdc++/libgcc_s provider per process. Repeat relevant Plasma acceptance.
No compiler or target-side build is required for these runtime checks.
