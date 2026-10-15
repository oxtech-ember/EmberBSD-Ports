# Stage the first GCC16 target runtime

This bootstrap prepares target CRT objects, libgcc, libstdc++ and C++ headers
from the audited GCC 16.2.0 source recipe. It supports explicit `amd64`
(`x86_64--netbsd`) and `aarch64` (`aarch64--netbsd`) targets.
The compiler and all build tools execute on the development host.
The target VM is only for execution and acceptance.

The output is an isolated **runtime-only bootstrap prerequisite**. It is not
a complete `gcc16-16.2.0nb1` package. It has no package database registration,
target compiler executables, complete compiler payload or package dependencies.
The separate `../runtime/` owner packages target DSOs as the explicit shared
`gcc16-runtime` provider. Runtime-only data must never be relabeled as the
complete compiler package.

## Inputs and provenance

Use a clean Ports revision and absolute paths without whitespace:

1. A prepared pkgsrc export with the current development-toolchain patches.
2. The original GCC archive whose SHA256 is in `../sources.tsv`.
3. A host-executable GCC16 kernel compiler built by
   `../cross/build.sh --target TARGET --kernel`. Keep its sibling `inputs.txt`.
   This bootstrap checks both compiler drivers, their target macros, the exact
   version, and the archive/patch-manifest hashes in that build receipt.
4. A complete EmberBSD base sysroot with headers, libc, pthread, libm, the
   loader and startup objects. Verify the original base/comp archive hashes
   against their EmberBSD release manifest before extraction. Record the full
   source revision in `EMBERBSD_SYSROOT_SOURCE`; optionally pass the external
   provenance file as `EMBERBSD_SYSROOT_PROVENANCE`.
5. Host static GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1 under one prefix. The
   existing `../cross/host-math.sh` prepares them. The builder also executes
   that workflow's GMP long-loop and periodic-signal contracts.
6. A new work directory on a case-sensitive volume, host C/C++ compilers,
   GNU make, tar, patch, realpath and shasum. Set `CROSS_JOBS` explicitly.

The seed checks reject the wrong ELF architecture, missing base inputs and
ELF links escaping the supplied sysroot. Use relative symlinks in the seed.
These checks cannot independently authenticate an EmberBSD fork revision.
The caller owns the verified release/source provenance; `inputs.txt` retains
the claim and hashes the selected headers, libraries and provenance file.
Do not relabel an upstream NetBSD or mixed sysroot as EmberBSD.

## amd64 command

Use this isolated build layout, or replace its absolute paths. The kernel compiler
must finish first. The host-native wrappers pass the macOS SDK `-isysroot`
to the actual host GCC16, including its configure tests.

```sh
HOST_CC=/absolute/build/host-native/bin/gcc \
HOST_CXX=/absolute/build/host-native/bin/g++ \
GNU_MAKE=/opt/homebrew/bin/gmake CROSS_JOBS=4 \
EMBERBSD_SYSROOT_SOURCE=c5d396f5698b68e956b29ee5b256bc7877e6c517 \
EMBERBSD_SYSROOT_PROVENANCE=/absolute/build/sysroot-seed-provenance.json \
sh profiles/development-toolchain/bootstrap/build.sh --target amd64 \
    /absolute/build/pkgsrc \
    /absolute/build/distfiles/gcc-16.2.0.tar.xz \
    /absolute/build/gcc-kernel/toolchain \
    /absolute/build/sysroot-seed \
    /absolute/build/host-math/prefix \
    /absolute/build/gcc-runtime-bootstrap
```

Insert `--check` before `--target` for a read-only preflight. It verifies
inputs and prints the target, ABI, flags and intended stage path. It creates
no work directory and does not compile a test or configure GCC.
Choose `--target aarch64` with that target's own compiler and complete seed.

## Build and ABI decisions

Source preparation uses the same GCC archive SHA256, RCS-filtered patch hashes,
zero-fuzz application and required modules repair as the cross workflow.
The native-only `patch-gcc_Makefile.in` is audited and omitted, as in that
workflow: a Darwin compiler prefix must not enter target driver links.
No extracted source file is edited outside this private work directory.

The NetBSD pkgsrc recipe changes `libstdc++-v3/configure` from
`libtool_VERSION=6:36:0` to `7:36:0`. This selects `libstdc++.so.7`.
The bootstrap applies that same substitution and checks the actual installed
SONAME. It retains the recipe's POSIX threads, shared libraries, long-long
support, disabled libstdc++ PCH, disabled libssp (SSP is in target libc),
and no zstd/Graphite provider. It retains the NetBSD API cache choices from
`Makefile.common`.

For amd64, configure and target compilation retain `nocona` architecture and
tuning with SSE floating point. This bootstrap is 64-bit only, following the
existing cross workflow's `--disable-multilib`. It does not qualify pkgsrc's
optional i386 multilib payload. Upstream symbol-versioning and dual-ABI
defaults remain unchanged.

Kernel mode disables threads. Its installed gthr headers therefore cannot
establish a POSIX-threaded libstdc++ build. The bootstrap configures a fresh
host frontend with shared libraries and POSIX threads enabled, builds
`all-gcc`, and checks `Thread model: posix`. It then runs the upstream targets
`all-target-libgcc` and `all-target-libstdc++-v3`. Upstream may build their
normal target prerequisites. It installs only `install-target-libgcc` and
`install-target-libstdc++-v3` with `DESTDIR=NEW_WORK/stage`.

The target prefix is `/usr/pkg/gcc16`, not the host work directory:

- CRT: `stage/usr/pkg/gcc16/lib/gcc/TRIPLET/16.2.0/crt{begin,end}*.o`.
- Libraries: `stage/usr/pkg/gcc16/lib/libgcc_s.so.1` and `libstdc++.so.7`.
- Headers: `stage/usr/pkg/gcc16/include/c++`, including the target directory.

The builder inspects all four shared/static CRT variants and both runtime
DSOs, checks SONAMEs and rejects build-host paths in dynamic tags.
It saves source/tool/seed hashes, configure/build/install logs, regular-file
checksums and a symlink inventory. `build-success` means staging checks passed;
it does not mean that a C++ process or a desktop ran successfully.

## Next compiler and package stages

Merge this stage only into a new private copy of the verified seed. Record
that union and preserve its base provenance. The development-host cross
builder needs the staged runtime, CRT and headers. The final VM receives only
the target DSOs through the separately checked `gcc16-runtime` package and
native target pkgtools. The selected provider has one version, ABI and prefix,
and conflicts with overlapping full `gcc16`/`gcc16-libs` packages.
Do not fabricate a `gcc16` package record. The common cross profile owns its
explicit runtime-provider guard and dependencies; this bootstrap changes none.

If a complete installable target compiler is requested later, it needs a
separate Canadian-cross recipe with
`build=development host`, `host=target EmberBSD`, and `target=target EmberBSD`.
Build it on the development host using the application cross compiler and
the staged target libraries. Cross-build all target dependencies, preserve
pkgsrc's full GCC payload and normal package checks, generate the real PLIST
and dependency metadata, and package it with native host pkgtools. Verify its
ELF files and run prebuilt C/C++/thread/exception consumers on the target.
This optional compiler package is separate from the runtime provider used by
desktop consumers. The VM does not need development tools for acceptance.
This bootstrap does not implement or claim that later compiler stage.

## Host checks and cleanup

```sh
sh profiles/development-toolchain/bootstrap/tests/inputs.sh
sh profiles/development-toolchain/bootstrap/tests/source.sh
```

The first fixture exercises argument, architecture, compiler, seed, source
receipt and ABI guards. The second uses real tar/patch operations and verifies
the modules repair, native-driver exclusion, ABI substitution, corrupt archive
rejection and refusal to overwrite sources. Neither compiles GCC or proves
runtime packaging. No real target runtime build is recorded for this helper.
The fixtures remove only their own temporary directories.

On a failed real build, preserve the work directory and its logs. The helper
does not delete caller inputs, install into `/usr/pkg`, modify the seed,
register packages, start a VM, or write a device. After acceptance and
preservation of the selected runtime and receipts, remove only the recorded
private source/frontend/object directories that are no longer needed.
