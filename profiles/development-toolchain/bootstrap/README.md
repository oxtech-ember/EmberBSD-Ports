# Stage the first GCC16 target runtime

This bootstrap prepares target CRT objects, libgcc, libstdc++ and C++ headers
from the audited GCC 16.2.0 source recipe. It supports explicit `amd64`
(`x86_64--netbsd`) and `aarch64` (`aarch64--netbsd`) targets.
Optional `--with-libgomp` and `--with-libatomic` flags add the same source
release's OpenMP and atomic runtimes. Without these flags the original library
selection is unchanged. Keep the flags before `--target`.
The compiler and all build tools execute on the development host.
The target VM is only for execution and acceptance.

For the bounded NetBSD locale source repair, the separate
[fresh libstdc++ helper](libstdcxx.md) uses an existing application compiler.
It verifies inherited runtime components and leaves this builder's strict
resume identities unchanged. Full rebuilt-library acceptance is separate.

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
   GNU make, tar, patch, realpath, shasum and cmp. Set `CROSS_JOBS` explicitly.

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
Both source audits accept literal `+` in canonical `libstdc++` patch basenames.
`tests/patch-names.rb EXPORTED_PKGSRC GCC_ARCHIVE NEW_WORK` checks the actual
audits with the current recipe, unsafe names and a corrupted patch hash.
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

The optional libraries retain GCC's actual NetBSD naming. `libgomp` uses
`libtool_VERSION=1:0:0`, and `libatomic` uses `3:0:2`; the bundled NetBSD
libtool selects its `sunos` version scheme. Their SONAMEs are therefore
`libgomp.so.1` and `libatomic.so.3`. Linux's atomic SONAME and the older base
OpenMP provider are not substitutes. No compatibility alias is added.
Both optional libraries use the existing source/patch audit and target tools;
the generated configure inputs are also hashed in `inputs.txt`.

The bootstrap selects GNU target binutils from the audited kernel compiler
prefix. It exports absolute `AR_FOR_TARGET`, `AS_FOR_TARGET`, `LD_FOR_TARGET`,
`NM_FOR_TARGET`, `RANLIB_FOR_TARGET`, `OBJCOPY_FOR_TARGET`, `OBJDUMP_FOR_TARGET`,
`READELF_FOR_TARGET` and `STRIP_FOR_TARGET` paths. That prefix also leads
`PATH` during configure and make. A development-host `nm` is not a substitute.
Each tool must report its GNU tool identity. The assembler must also report
the selected target triplet. The hashes and audited prefix identify tools such
as `ar` and `nm`, which do not report a target triplet. The compiler and target
ELF preflight checks establish the selected target.

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
When requested, the corresponding `all-target-libgomp`/`libatomic` and
`install-target-libgomp`/`libatomic` targets are included. A prerequisite being
built does not imply that it was installed or included in the runtime package.
The unique `runtime_libraries` receipt records the exact ordered selection.

The target prefix is `/usr/pkg/gcc16`, not the host work directory:

- CRT: `stage/usr/pkg/gcc16/lib/gcc/TRIPLET/16.2.0/crt{begin,end}*.o`.
- Libraries: `stage/usr/pkg/gcc16/lib/libgcc_s.so.1` and `libstdc++.so.7`, plus
  `libgomp.so.1` and/or `libatomic.so.3` when explicitly selected.
- Headers: `stage/usr/pkg/gcc16/include/c++`, including the target directory.

Configure explicitly sets `--with-toolexeclibdir=/usr/pkg/gcc16/lib` for
the target libraries. `--libdir` alone does not override upstream cross-host
defaults: libgcc and libstdc++ otherwise install under `PREFIX/TRIPLET/lib`.
The configured directory also owns libtool install metadata. The builder
does not flatten or copy files from an incorrect installation afterwards.

The builder inspects all four shared/static CRT variants and every selected runtime
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
sh profiles/development-toolchain/bootstrap/tests/binutils.sh
sh profiles/development-toolchain/bootstrap/tests/runtime-resume.sh
sh profiles/development-toolchain/bootstrap/tests/runtime-libraries.sh
ruby profiles/development-toolchain/bootstrap/tests/runtime-layout.rb \
    /absolute/prepared-gcc-source
```

The first fixture exercises argument, architecture, compiler, seed, source
receipt and ABI guards. The second uses real tar/patch operations and verifies
the modules repair, native-driver exclusion, ABI substitution, corrupt archive
rejection and refusal to overwrite sources. Neither compiles GCC or proves
runtime packaging. These host checks do not establish a successful runtime build.
The binutils fixture checks exported absolute tools, command-name lookup and
rejection of a non-GNU `nm`. The input fixture also checks resume provenance,
preserved objects and invalidation of failed configure/map/archive outputs.
The runtime recovery fixture checks full partial-stage preservation, target
metadata invalidation, object reuse and rejection of changed frontend state.
The layout fixture executes the install-directory shell sections from the
actual prepared upstream configure scripts. It checks both target identities,
the incorrect default and the explicit directory. It also executes the actual
top configure recursion parser and Makefile removal loops with production
configure arguments. Runtime-only recovery must retain host/build Makefiles;
normal fresh and frontend recovery modes keep upstream invalidation behavior.
It does not configure or
build GCC, run a linker or establish installed runtime acceptance.
The optional-library fixture checks selection, refusal of library removal,
completed-stage file/link drift and preservation of stage/receipt/frontend
state. Its text payload is deliberately not target ELF. The source layout
check also executes GCC's actual NetBSD libtool version branch and verifies
the pinned OpenMP/atomic SONAME calculations.
The fixtures remove only their own temporary directories.

## Resume an incomplete runtime build

Use the same inputs and host compiler settings as the original invocation.
Add `--check --resume` before `--target` for a read-only preflight. It verifies
all previously recorded input hashes, seed identity, target, host settings and
the completed POSIX-thread frontend. It rejects a successful or installed stage.

After that check, replace `--check --resume` with `--resume` in the same command.
Use an immutable export of the chosen Ports commit for the helper. Keep that
export while its hashes are referenced by the runtime receipt.
The helper preserves the original receipt and logs in `WORK/resume.XXXXXX`.
It records the current helper, prepared configure files and GNU tool hashes in
`inputs.txt`. It repeats configure and the upstream make targets in the existing
build directory. It does not extract sources or clean compiler/object files.

The generated GCC `nm`, configure caches and generated sub-Makefiles must be
recreated. GCC otherwise reuses an executable `./nm` and an empty cached tool
selection. The helper moves that state into the resume backup. It also moves
libgcc map files, their temporary output and incomplete archives/shared libraries.
These outputs must be regenerated with the corrected tools. Frontend and target
object files remain available for the normal incremental make rules.

## Recover only the target-library installation layout

For completed POSIX frontends followed by an incorrect target-library install,
use `--check --resume-runtime` with the original inputs and host settings.
This mode requires the explicit GNU target-binutils receipt and all completed
frontend configure files and language executables. A completed accepted stage
is refused unless the explicit library selection strictly adds runtimes as
described below. The read-only check does not move or configure anything.

After review, replace `--check --resume-runtime` with `--resume-runtime`.
The helper preserves the old receipt, logs and top configure files in
`WORK/resume-runtime.XXXXXX`. It inventories and checksums the entire partial
stage, moves that stage into the backup, verifies it and creates an empty stage.
The old installation cannot become the accepted runtime provider.
Verification compares the complete path inventory and symlink targets after
the move. Regular-file counts must match the checksum manifest. SHA256 file
verification is skipped only when there are zero regular files and the
manifest is empty. Empty stages and stages with only directories or symlinks
retain the inventory checks. The new empty stage is created only after these
preservation checks pass.

Only target-library Makefiles, configure caches/status/logs, libtool scripts
and `.la`/`.lai` metadata are moved out of the build tree. Target objects,
archives, shared libraries and libgcc symbol maps stay available. Top configure
then passes the canonical `--with-toolexeclibdir` option to those libraries.
No post-install rename or flattening substitutes for upstream installation.

Runtime-only top configure uses upstream `--no-recursion`. Without this option,
top configure deletes existing host/build Makefiles on every invocation, even
when its other arguments do not change. Target Makefiles have already been
invalidated explicitly. Keeping host/build Makefiles lets upstream make reuse
the completed frontend without reconfiguring it.

The GCC subdirectory retains its Makefile, cache, auto-host header and configure
arguments. This mode skips the direct `all-gcc` step. Upstream target-library
dependencies may enter the normal incremental `all-gcc` rule; its configure
rule reuses the existing GCC Makefile. Hashes of frontend configuration and
`xgcc`, `cc1` and `cc1plus` must stay unchanged after top configure, library make
and installation. A change fails recovery. Normal ELF, SONAME, dynamic-path,
header and stage-receipt checks remain mandatory after the clean installation.

A work tree already missing frontend state after a failed configure remains
ineligible for runtime-only resume. This mode does not silently restore old
Makefiles or accept a changed frontend hash. Preserve the failed tree and its
backup for explicit, separately verified recovery.

## Add libraries to a completed stage

Use the original inputs and host settings with an explicit superset, for example
`--check --resume-runtime --with-libgomp --with-libatomic --target aarch64`.
The existing source/tool hashes and POSIX frontend must still match. The check
also compares every completed-stage regular-file hash and symlink with the
recorded inventories and rejects special files. Missing, added or changed
files/links fail. A repeated selection or removal of a previously selected
library does not authorize rebuilding an accepted stage.

For the build, remove only `--check`. The existing stage is preserved by the
same verified runtime-resume backup. Its original success marker and stage
manifests are retained, and the active success marker is removed before the
new stage can be installed. The prior input receipt remains in the backup;
the active receipt has one updated library-selection line. Completed frontend
configuration and executable hashes must remain unchanged. The usual source,
SONAME, header, dynamic-path and stage checks apply to the new installation.
Package this new stage with the common runtime owner; never register a second
OpenMP/atomic provider or copy a base library under the requested filename.

Host selection/packaging tests do not qualify these optional libraries.
Before acceptance, run prebuilt GCC16 OpenMP parallel-work and atomic-operation
contracts in EmberBSD and verify the loaded library hashes. The actual target
runtime extension and these execution checks remain separate gates.

On a failed real build, preserve the work directory and its logs. The helper
does not delete caller inputs, install into `/usr/pkg`, modify the seed,
register packages, start a VM, or write a device. After acceptance and
preservation of the selected runtime and receipts, remove only the recorded
private source/frontend/object directories that are no longer needed.
