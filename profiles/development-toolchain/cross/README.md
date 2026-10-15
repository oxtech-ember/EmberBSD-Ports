# GCC16 cross compiler for EmberBSD

Cross-compilation is the preferred build path: build GCC 16.2.0 on the
development host and execute the resulting programs on EmberBSD. The tested
hosts are Apple Silicon macOS (application mode) and Debian x86_64 Linux
(kernel mode). There is no NetBSD-host
check in the compiler build or compile-only acceptance scripts. The separate
target runner requires the selected EmberBSD/NetBSD architecture because it
executes target ELF files. VM and boards run acceptance tests only.

Target-dependent entry points accept `--target aarch64|amd64`. The default is `aarch64`.
Unknown, empty and repeated target options fail before output creation.

| Target | GNU triplet | Validation |
| --- | --- | --- |
| `aarch64` | `aarch64--netbsd` | Host builds and target checks recorded below |
| `amd64` | `x86_64--netbsd` | Host orchestration fixtures only; real build and runtime checks pending |

The triplets follow the fork's [machine selection](https://github.com/oxtech-ember/EmberBSD/blob/main/build.sh)
and [GNU platform definitions](https://github.com/oxtech-ember/EmberBSD/blob/main/share/mk/bsd.own.mk).
The same selected triplet controls binutils, compiler configuration, startup
objects and target C++ headers. It is recorded in `inputs.txt`.

The compiler uses the same verified original GCC archive and frontend
portability patches as the Ports native package, including the nb1 C++
modules repair. The default application mode uses an accepted sysroot's GCC16
headers/runtime. `--kernel` builds C/C++ frontends without a userland sysroot,
shared libraries or target threads. Both modes install only the compiler;
neither rebuilds the target runtime or creates a distribution image.

## Application inputs

Prepare the development-toolchain or common-tools pkgsrc export using
[the parent profile](../README.md). Record the Ports commit and the sysroot's
source/package revisions and checksums. The archive URL and SHA256 are in
[the shared source manifest](../sources.tsv). Keep binary inputs outside Git.

Provide these absolute paths without whitespace:

1. The prepared pkgsrc tree containing `lang/gcc16` and the modules repair.
2. The original `gcc-16.2.0.tar.xz` archive.
3. An EmberBSD sysroot for the selected target with `/usr/include`, startup objects, libc,
   pthread and math libraries, loader, and the selected `/usr/pkg/gcc16`
   headers/runtime. Preserve relative symlinks. Resolve links escaping the
   sysroot when creating the snapshot; never resolve them against the host.
4. A host `TOOLDIR` produced by the fork's
   [cross-build path](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/cross-build.md).
   GNU make builds the compiler, and its selected target binutils are copied into the
   compiler prefix. Qualifying current binutils remains separate work.
5. A new work directory with room for sources, objects and the compiler.

Repair missing cross support through Ports or the OS. The compiler and
linker must run on the build host. The sysroot libraries
and startup objects must belong to the target. Equal CPU architecture does
not make Darwin and NetBSD executables interchangeable.

```sh
HOST_CC=cc HOST_CXX=c++ \
    sh profiles/development-toolchain/cross/build.sh \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz /absolute/sysroot \
    /absolute/os-build/tools /absolute/new-gcc-cross
```

For amd64, use a matching amd64 sysroot and fork-built x86_64 binutils:

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=2 \
    sh profiles/development-toolchain/cross/build.sh --target amd64 \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz /absolute/sysroot-amd64 \
    /absolute/os-build-amd64/tools /absolute/new-gcc-cross-amd64
```

The sysroot must already contain the matching GCC16 target runtime and C++
headers. Kernel mode cannot provide them. Do not substitute AArch64 packages
or base-compiler runtime files. The host needs C/C++ compilers, a POSIX shell,
`awk`, `shasum`, `tar`, `patch`, and the fork's host GNU make and binutils.
Automatic host math preparation also uses `curl` for missing archives.

The five-argument command builds GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1 under
`NEW_WORK/host-math`. It downloads missing pinned archives into
`NEW_WORK/host-archives`. `EMBER_HOST_MATH_ARCHIVES` can name an existing cache
containing `gmp-6.3.0.tar.xz`, `mpfr-4.2.2.tar.bz2` and `mpc-1.4.1.tar.xz`.
Original URLs and SHA256 are in [host sources](host-sources.tsv) and the
[shared manifest](../sources.tsv).

For reuse, `host-math.sh ARCHIVE_DIRECTORY NETBSD_TOOLDIR NEW_WORK` prepares
the libraries separately. Pass its `NEW_WORK/prefix` through
`EMBER_HOST_MATH_PREFIX`, or as an optional argument immediately before the
compiler's `NEW_WORK`. Do not reuse the fork's old GMP 6.2.1 host library.
The helper verifies every archive before extraction, builds static libraries,
and runs their upstream test suites. It also checks long GMP loops with and
without signal delivery. Nothing is installed into a shared prefix. The GCC
recipe verifies the selected library versions and reruns this host contract before
compiler configuration. It records hashes of the three static libraries.
The helper selects `-O2 -std=gnu17` for the host C libraries explicitly:
GMP 6.3.0's configure probes require pre-C23 empty-parameter-list semantics.
This keeps the selected host compiler and all upstream tests. The input record
includes compiler versions/triplet, C/C++ flags and source/library hashes.

GMP 6.2.1 uses the reserved Darwin `x18` register in ARM64 assembly. During a
LiteRT build this caused intermittent compiler crashes in GMP/MPFR constant
evaluation. The compiler's attempt to print a backtrace then failed in Apple
libunwind. [Upstream identifies the ABI defect](https://gmplib.org/#STATUS);
[the register repair](https://gmplib.org/list-archives/gmp-commit/2020-November/003062.html)
is included in GMP 6.3.0. Updating the host library fixes the prerequisite;
compiler retries and lower job counts are not used as a substitute.

The recipe verifies the GCC SHA256 and recorded RCS-filtered patch hashes
before extraction. It applies the source patches with zero fuzz. As in the
native common profile, Graphite/ISL is disabled. The source archive does not
contain ISL; its unused distinfo entry is excluded explicitly.

One additional cross-only difference is necessary: `patch-gcc_Makefile.in`
is verified but not applied. That native pkgsrc patch embeds the compiler's
installation prefix as target runtime search paths. On macOS that would
leak a Mac path into the ELF link or fail linking outright. The cross build
retains upstream's default driver search logic. The acceptance recipe
selects the target GCC16 startup objects, headers and runtime explicitly.
This does not remove the RPATH repair from native packages.

The recipe installs into `new-gcc-cross/toolchain` and records inputs and
build logs in the work directory. It never writes `/usr/bin`, `/usr/pkg`,
`/etc/mk.conf` or a board. Keep the work directory and sysroot at their
recorded paths. `HOST_CC`/`HOST_CXX` name the existing host compilers;
`CROSS_JOBS` optionally overrides concurrency. Both recipes default to the
host's online CPU count from `getconf`, with `sysctl` as a fallback.
A failed stage returns nonzero.

The installed prefix includes GCC's `<triplet>/bin` tool-search
directory. This is required for the driver's `-gsplit-dwarf` invocation of
`objcopy`, even when ordinary compilation already works. The build runs
`tests/split-dwarf.sh --target TARGET CROSS_PREFIX NEW_WORK` with a clean PATH and no
`-B` or compiler-search overrides. The resulting DWARF5 skeleton and DWO
must both be readable and retain the named type. This contract passed on
2026-10-08 with the current GMP-backed GCC16 prefix.

## Kernel frontends without a sysroot

Use the same prepared pkgsrc export, pinned GCC archive, fork-built host
TOOLDIR and current host math libraries. Omit the application sysroot:

```sh
HOST_CC=gcc HOST_CXX=g++ CROSS_JOBS=4 \
    sh profiles/development-toolchain/cross/build.sh --kernel \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/os-build/tools /absolute/host-math/prefix /absolute/new-gcc-kernel
```

Add `--target amd64` before or after `--kernel` for x86_64 kernel frontends.
This changes no application sysroot requirements.

The optional host math prefix works as in application mode: leave it out to
build isolated prerequisites, or set `EMBER_HOST_MATH_PREFIX`. Kernel mode uses
`--without-headers --disable-shared --disable-threads` and builds/installs
`all-gcc`/`install-gcc`. It retains patch verification, the modules repair,
target binutils copies, native-only RPATH patch exclusion and the installed
split-DWARF contract. Select its `NEW_WORK/toolchain` through the fork's
`EMBER_EXTERNAL_TOOLCHAIN`; inspect the owning OS wrapper for host-tool selection
and kernel inputs. Compiler preparation alone does not establish kernel build
or boot acceptance.

On 2026-10-11, the public recipe built GCC16.2 with host GCC16.2 on Debian
x86_64 Linux, passed its installed split-DWARF contract, and cross-built the
OS revision `d472eb8fecc3ff70b6aa231888b301414985845c`: EMBER64 kernel and image,
four modules and three board DTBs. The OS wrapper's portable contracts passed
with GCC16. Boot, the four native contracts and Linux-hosted application-mode
runtime acceptance remain unverified.

For an application SDK that lacks `libatomic`, the
[atomic component](../../../pkgsrc/local-robotics/gcc16-libatomic/README.md)
uses the same GCC16 source and ABI. Its [cross helper](build-libatomic.sh)
stages the runtime without replacing a complete GCC16 provider. The
[PCL acceptance](../../../probes/pcl/VALIDATION.md) checks the component's
256-byte operations, concurrent updates and actual AArch64 package lifecycle.

Run the argument/prerequisite and real export regressions with:

```sh
sh profiles/development-toolchain/cross/tests/build-modes.sh
sh profiles/development-toolchain/cross/tests/build-modes.sh --target amd64
sh profiles/development-toolchain/cross/tests/targets.sh
sh profiles/development-toolchain/cross/tests/configure-targets.sh
sh profiles/development-toolchain/cross/tests/runtime-checker.sh
sh profiles/development-toolchain/tests/prepare.sh /absolute/new-pkgsrc-test
```

The first five commands use host fixtures. They check argument rejection,
target-specific runtime/binutils selection, compile flags, and both configure
modes. Runtime receipts also reject corruption, foreign paths and duplicate
libraries without a target compiler. The configure fixture stops before
building GCC. These checks do not
prove amd64 compilation, ELF contents or runtime behavior. `build-modes.sh`
also accepts an optional real `NETBSD_TOOLDIR` after the target option.

The last command retains a complete development-toolchain export. It exercises
`prepare-pkgsrc.sh` against the pinned submodule with GNU patch's zero-fuzz
application and verifies the package revisions and source patch hashes.

## Compile here, execute on EmberBSD

```sh
sh profiles/development-toolchain/cross/compile-tests.sh \
    /absolute/new-gcc-cross/toolchain /absolute/sysroot /absolute/new-tests
```

Pass `--target amd64` for an amd64 prefix and sysroot. The output includes
`target.txt` and the target-option helper. Keep both with the test programs.

This reuses the native C11 atomics/TLS and C++20 DSO test sources. It compiles
C with and without LTO, and C++ with threads, TLS, strings and exceptions
crossing a shared-library boundary. A floating constant-evaluation regression
includes `_Float32` limits and target long-double exponentiation.
It checks dynamic dependencies for host
path leakage. Compilation alone is not runtime acceptance.

Copy the complete `new-tests` directory to a scratch directory on the target,
then run:

```sh
sh /absolute/target-tests/run-target.sh /absolute/target-tests
```

For amd64, add `--target amd64` before the directory. The runner checks the
host architecture and the compiled target receipt before executing programs.

For archives made on macOS, use `COPYFILE_DISABLE=1 tar --no-xattrs --no-acls
--no-fflags ...` so NetBSD tar does not fail restoring Apple metadata.
The target runner checks actual loaded `libstdc++` and `libgcc_s` identities
against SHA256 receipts made from the accepted sysroot. Both libraries must
resolve inside `/usr/pkg/gcc16`. It does not need a compiler on the target.
Loader overrides
are rejected. It does not install packages or change login defaults.

## Validation boundary

On 2026-10-11, the revised host-math recipe completed with GCC/G++ 16.2.0 on
Debian 13/x86_64 using four workers and explicit GNU C17 flags. GMP passed
177 tests with one upstream skip (`t-addaddmul`, whose native primitive is
absent on this host); MPFR passed all 198 and MPC all 75. The GMP long-loop
and periodic-signal contracts also passed. This validates host prerequisites;
it does not establish target application runtime or Linux kernel acceptance.
Separately, this compiler's `--kernel` mode built the full EmberBSD kernel,
four matched modules, and three DTBs on that Linux host. Portable contracts
and all nine artifact hashes passed; see the [OS-owned evidence](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/cross-build.md#linux-gcc16).
Native contracts, boot, and hardware acceptance remain separate.

On 2026-10-07, the rebuilt GCC 16.2.0 passed host compilation and target
acceptance with GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1. That build explicitly used
four jobs; the recipe's current default uses the detected host CPU count.
GMP's upstream test groups
had no failures. MPFR passed 195 tests with three skips; MPC passed all 75.
The reserved-register regression established the following on Apple Silicon:

| Host arithmetic implementation | Long-loop contract |
| --- | --- |
| Original GMP 6.2.1 ARM64 assembly | Four of four executions faulted |
| Same library with generic upstream `add_n` | Four of four passed |
| Same native `add_n`, only `x18` changed to `x17` | Six of six passed |
| GMP 6.3.0 | Passed with and without periodic signals |

The new static GMP archive contains no instructions using `x18`. The rebuilt
compiler passes the floating constant regression and the original protobuf
and RE2 compilation commands that exposed the failures.

The cross C11/C++20 contracts passed on physical Orange Pi Zero 3W (Allwinner
A733), NetBSD 11.0/AArch64, at 20:46 UTC on 2026-10-07. Execution took 0.18 s.
The DSO contract confirmed actual loading of `/usr/pkg/gcc16/lib/libstdc++.so.7`
and `/usr/pkg/gcc16/lib/libgcc_s.so.1` from the existing GCC16 nb1 runtime.
The board's firmware and hardware revision were not requalified by this test.
This covers the focused source scenarios, not the full upstream compiler
suite, arbitrary Ports packages, a full GCC16-built OS or GPU acceleration.

The common `mk.conf` still describes the **installed native compiler** policy.
Do not feed a target `/usr/pkg/gcc16/bin/gcc` to a Darwin build process.
General pkgsrc cross-package orchestration and Canadian-cross building of
an installable target GCC package require separate build/host/target handling.
The standalone cross compiler here is immediately usable for target source
compilation; its availability does not establish those package workflows.
