# Cross compiler and target checks for EmberBSD

Host controllers use Python 3.15 and its standard library. Set
`export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK`, or pass `--sdk-source SOURCE`
to each Python entry point. The source must provide `emberbsd_sdk` API1 under
`src/`. Imports do not download, build or install the SDK. Target execution
scripts under `cross/tests/target/` use only the target's POSIX shell.

Cross-compilation is the preferred build path: build GCC 16.2.0 on the
development host and execute the resulting programs on EmberBSD. The tested
hosts are Apple Silicon macOS (application mode) and Debian x86_64 Linux
(kernel mode). There is no NetBSD-host
check in the compiler build or compile-only acceptance scripts. The separate
target runner requires the selected EmberBSD/NetBSD architecture because it
executes target ELF files. VM and boards run acceptance tests only.

Application and runtime entry points accept `--target aarch64|amd64`. The default is `aarch64`.
Unknown, empty and repeated target options fail before output creation. The
kernel compiler, Binutils builder and compiler probes additionally accept the
kernel-only `earmv7hf` target; the ordinary compiler and runtime interfaces
continue to reject it.

| Target | GNU triplet | Validation |
| --- | --- | --- |
| `aarch64` | `aarch64--netbsd` | GCC16 cross C/C++ LTO links with Ports Binutils 2.47; target checks remain separate |
| `amd64` | `x86_64--netbsd` | Real macOS arm64 application build, POSIX threads, split DWARF and installed EmberBSD 11.0 runtime contracts pass |
| `earmv7hf` | `armv7--netbsdelf-eabihf` | Kernel-only; verifies GCC hard-float macros and a freestanding ELF32 ARM relocatable object |

The triplets follow the fork's [machine selection](https://github.com/oxtech-ember/EmberBSD/blob/main/build.sh)
and [GNU platform definitions](https://github.com/oxtech-ember/EmberBSD/blob/main/share/mk/bsd.own.mk).
The same selected triplet controls binutils, compiler configuration, startup
objects and target C++ headers. It is recorded in `inputs.txt`.

The [amd64 runtime acceptance](../runtime/README.md#amd64-installed-acceptance)
covers the nb6 package lifecycle and prebuilt C11/C++20, TLS, DSO, OpenMP
and generic atomic consumers. Only runtime libraries are installed on the
target. The target retains its existing base. A new source-built sysroot,
VM/image integration and Plasma retain separate acceptance boundaries.

The recipe uses GCC 16 host compilers by default: `gcc-16` and `g++-16`.
Both must report GCC major version 16. Clang cannot build this cross toolchain.
The standalone [common Binutils producer](binutils.md) independently selects
the native Ports prefix and defaults to Clang. It also supplies the matching
host BFD headers and libraries for native OS helper integration.

`build.py` builds the host-runnable Binutils 2.47 tools from the pinned
Common Ports source and patch set. It installs the selected triplet tools and
the linker's full `lib/ldscripts` tree in the GCC prefix before it configures
GCC. GCC's default `as` and `ld` paths point to those tools. No `-B` or specs
file is required. `inputs.txt` records the archive and patch hashes.
`linker-scripts.sha256` records the installed scripts. The AArch64 cross
profile checks current Binutils with C and C++ LTO. It does not run target ELF.

The separate relocation fixture checks secondary emulations in an OS tool
directory without compiling GCC:

```sh
python3 -B profiles/development-toolchain/cross/tests/linker-relocation.py \
    /absolute/os-tools amd64 /absolute/new-relocation-receipt
```

This fixture checks path relocation only. It does not qualify amd64 builds,
a complete OS build or booting a BIOS loader.

The compiler uses the same verified original GCC archive and frontend
portability patches as the Ports native package, including the nb1 C++
modules repair. The default application mode uses an accepted sysroot's GCC16
headers/runtime. `--kernel` builds C/C++ frontends without a userland sysroot,
shared libraries or target threads. Both modes normally install only the compiler.
The explicit `--kernel --bootstrap-libgcc` option also builds static support
for the first OS seed. None of these modes builds the POSIX target runtime or
creates a distribution image.

The ARMv7 target is available only through kernel-oriented entry points. Build
its compiler with `build.py --target earmv7hf --kernel`; this keeps
`earmv7hf` out of the application `TARGETS` table and does not qualify an
application sysroot or runtime. The build verifies the compiler's EABI
hard-float macros, compiles a freestanding floating-point object, checks for
ELF32 machine 40, EABI5, and the VFP-register calling-convention attribute.
It then links that object without libc and verifies the hard-float EABI flag
on the linked ELF; ARM relocatable objects carry the calling convention in
`.ARM.attributes` instead of the linked-image flag.
The GCC16 package patch limits the inherited `-matpcs` assembler option to an
explicit APCS/ATPCS ABI selection. The default AAPCS hard-float path otherwise
crashes GAS 2.42 and 2.47 on ARM ELF; the compiler build's split-DWARF and ABI
object probes exercise the corrected path.
When `--bootstrap-libgcc` is selected, its header input must come from the
`earmv7hf` build. The `machine` include link must resolve to `arm`, and the
sysroot must include `arm/ansi.h` plus the public `evbarm` headers
`disklabel.h`, `intr.h`, and `sljit_machdep.h`.

The explicit [Fortran application mode](fortran.md) adds the same GCC16
frontend in a new compiler generation. Its compile-only capability receipt
does not qualify target linking or the Fortran runtime.

The separate [firmware entry point](firmware.md) prepares an explicit
`arm-none-eabi` C frontend without extending the OS target policy.

## Shared compiler acceptance

`compile-tests.py` defaults to the selected Clang SDK toolchain. Select GCC
explicitly with `--compiler-family gcc`; the compiler family is never inferred
from a build failure. `--host-prefix` selects the same native Ports prefix used
by the SDK for Clang controller tools. `--os-source` adds the OS-owned target
runtime regressions (`libc-aliases`, base loader, and shared-memory fork/CAS)
to this bundle. It records the OS test-source revision and hashes separately
from the OS build revision. The bundle remains a compile result until its
`run-target.sh` suite executes on the target.

```sh
/absolute/native-prefix/bin/python3.15 -B profiles/development-toolchain/cross/compile-tests.py \
    --compiler-family clang --host-prefix /absolute/native-prefix \
    --os-source /absolute/EmberBSD \
    /absolute/clang-cross /absolute/sysroot /absolute/new-target-tests \
    --sdk-source /absolute/EmberBSD-SDK
```

The OS source option is optional for the ordinary Ports test bundle. When it is
present, the guest suite requires all OS-owned programs and reports nonce-bound
check events after each successful check. It does not install compilers or
developer tools in the guest.

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
   [cross-build path](https://github.com/oxtech-ember/EmberBSD/blob/main/tools/docs/cross-build.md).
   Its host GNU make builds GCC. The recipe builds target Binutils 2.47 from
   the pinned Ports source and patches.
5. A new work directory with room for sources, objects and the compiler.

Repair missing cross support through Ports or the OS. The compiler and
linker must run on the build host. The sysroot libraries
and startup objects must belong to the target. Equal CPU architecture does
not make Darwin and NetBSD executables interchangeable.

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 \
    python3 -B profiles/development-toolchain/cross/build.py \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz /absolute/sysroot \
    /absolute/os-build/tools /absolute/new-gcc-cross
```

For amd64, use a matching amd64 sysroot. The recipe builds the selected
`x86_64--netbsd` Binutils 2.47 tools:

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=2 \
    python3 -B profiles/development-toolchain/cross/build.py --target amd64 \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz /absolute/sysroot-amd64 \
    /absolute/os-build-amd64/tools /absolute/new-gcc-cross-amd64
```

The sysroot must already contain the matching GCC16 target runtime and C++
headers. Kernel mode cannot provide them. Do not substitute AArch64 packages
or base-compiler runtime files. The host needs GCC/G++ 16, a POSIX shell,
`awk`, `shasum`, `tar`, `patch`, `curl`, and the fork's host GNU make.
The recipe downloads Binutils 2.47 unless `EMBER_BINUTILS_ARCHIVE` names a
cached archive. It checks the pinned SHA256, SHA512, and size before extraction.
Automatic host math preparation also downloads missing archives.

The five-argument command builds GMP 6.3.0, MPFR 4.2.2 and MPC 1.4.1 under
`NEW_WORK/host-math`. It downloads missing pinned archives into
`NEW_WORK/host-archives`. `EMBER_HOST_MATH_ARCHIVES` can name an existing cache
containing `gmp-6.3.0.tar.xz`, `mpfr-4.2.2.tar.bz2` and `mpc-1.4.1.tar.xz`.
Original URLs and SHA256 are in [host sources](host-sources.tsv) and the
[shared manifest](../sources.tsv).

For reuse, `host-math.py ARCHIVE_DIRECTORY NETBSD_TOOLDIR NEW_WORK` prepares
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

On macOS, set `SDKROOT=$(xcrun --show-sdk-path)` when the selected host GCC
cannot locate the system library. The Ports producer policy passes this selected
SDK to captured and logged commands on Darwin. A nonempty value must name an
existing absolute directory. Explicit command environment values take precedence;
an empty value keeps compiler-default selection available. Other hosts do not
inherit ambient `SDKROOT`. Ambient `CONFIG_SITE` and unrelated variables remain
excluded by the SDK's shared environment sanitizer.
The host GMP suite uses a
[type-correct variadic test adaptation](patches/README.md): `t-rand` must pass
`unsigned long` to `gmp_randinit`, as required by the upstream API. The original
GCC16.2/Darwin run fails; the same test with correct argument types passes
against the unchanged library. The helper pins the patch and keeps the full
upstream suites mandatory. This repair does not establish a compiler or
target build result by itself.

The standalone regression uses the same pinned archive and patch:

```sh
python3 -B profiles/development-toolchain/cross/tests/host-gmp-rand.py \
    /absolute/gmp-6.3.0.tar.xz /absolute/new-gmp-rand-check
```

It builds one static host library with GCC16. It preserves the original and
patched `t-rand` runtime statuses and diagnostics. The patched test must pass
both upstream value tables and four print-mode checks. An independent C type
assertion rejects the original three variadic calls and each individual
missing-cast mutant. This control works even when an ABI hides the runtime
error. The library hash must remain unchanged across the comparison.

Use `--require-baseline-failure` when reproducing the original runtime failure.
Use `--sanitize` for ASan/UBSan on supported hosts. `GMAKE` selects GNU make.
`HOST_CPPFLAGS` and `HOST_LDFLAGS` can select an explicit host SDK. The work
directory retains source copies, command logs, a compilation database and
`results.json`. This focused check does not replace the full host-math suites
or establish a target build. GMP's original license headers remain intact.

On Apple Silicon macOS, GCC16.2 with ASan/UBSan reproduces original exit 1
and patched exit 0. All value, print and individual missing-cast controls pass.
GCC's analyzer and Clang Static Analyzer report no findings in either test.
Cppcheck retains the same two upstream const-style findings in both versions.
Valgrind is not supported on this host. Assembly is outside sanitizer coverage;
this test does not qualify the complete library or a target system.

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
recorded paths. `HOST_CC`/`HOST_CXX` default to `gcc-16` and `g++-16`.
Explicit overrides must also select GCC 16;
`CROSS_JOBS` optionally overrides concurrency. Both recipes default to the
host's online CPU count from `getconf`, with `sysctl` as a fallback.
A failed stage returns nonzero.

The installed prefix includes GCC's `<triplet>/bin` tool-search
directory. This is required for the driver's `-gsplit-dwarf` invocation of
`objcopy`, even when ordinary compilation already works. The build runs
`tests/split-dwarf.py --target TARGET CROSS_PREFIX NEW_WORK` with a clean PATH and no
`-B` or compiler-search overrides. The resulting DWARF5 skeleton and DWO
must both be readable. The script checks the skeleton/split units and the
record name in the DWO string-offset table.

The AArch64 build also runs `tests/lto-binutils.py CROSS_PREFIX NEW_WORK`.
It checks default tool selection and compiles freestanding C and C++ with
LTO. The link trace must name GCC's `collect2`, plugin, and `lto-wrapper`,
plus the selected Ports `as` and `ld`. `readelf` must report AArch64 ELF
executables. This check proves cross compile and link only. It does not prove
target runtime without an accepted sysroot and target runner.

`tests/plugin-needed-warnings.py [--target TARGET] CROSS_PREFIX SYSROOT NEW_WORK`
checks the Binutils `ldelf.c` patch. It selects the matching compiler triplet
and checks its ABI. The default target is `aarch64`; `--target amd64` selects
`x86_64--netbsd`. It links a shared object that uses only libm, with
the GCC LTO plugin and `--fatal-warnings`, with and without
`--copy-dt-needed-entries`. The libc warning sections that libm brings in
through `DT_NEEDED` must not give warnings. A direct `gets` reference to
libc must still stop the link. This check needs an accepted sysroot for the
selected target, including its GCC16 CRT and `libgcc` files under
`usr/pkg/gcc16`. It selects these startup objects and libraries explicitly.
It checks cross links only; it does not execute target code.

The amd64 check passes on macOS arm64 with GCC 16.2.0, patched Ports
Binutils 2.47 and a source-built EmberBSD 11.0 sysroot. Both indirect cases
link without warnings. The direct `gets` reference still fails with a link warning.

## Kernel frontends without a sysroot

Use the same prepared pkgsrc export, pinned GCC archive, fork-built host
TOOLDIR, GCC16 host compilers and current host math libraries. Omit the
application sysroot:

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=4 \
    python3 -B profiles/development-toolchain/cross/build.py --kernel \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/os-build/tools /absolute/host-math/prefix /absolute/new-gcc-kernel
```

Add `--target amd64` before or after `--kernel` for x86_64 kernel frontends.
This changes no application sysroot requirements.

The optional host math prefix works as in application mode: leave it out to
build isolated prerequisites, or set `EMBER_HOST_MATH_PREFIX`. Kernel mode uses
`--without-headers --disable-shared --disable-threads` and builds/installs
`all-gcc`/`install-gcc`. It retains patch verification, the modules repair,
Ports Binutils 2.47, native-only RPATH patch exclusion, and the installed
split-DWARF and LTO contracts. Select its `NEW_WORK/toolchain` through the fork's
`EMBER_EXTERNAL_TOOLCHAIN`; inspect the owning OS wrapper for host-tool selection
and kernel inputs. That prefix's `bin` keeps the Binutils programs
`share/mk/bsd.own.mk` assigns for `EXTERNAL_TOOLCHAIN`: `ar`, `as`, `elfedit`,
`ld`, `nm`, `objcopy`, `objdump`, `ranlib`, `readelf`, `size`, `strings`, and
`strip`. The kernel link runs `${SIZE}` after it links. The build checks this
set again after `install-gcc` and stops if any tool is missing, naming the
missing tools and the required list. `addr2line` and `c++filt` are not part of
that contract. Compiler preparation alone does not establish kernel build
or boot acceptance.

### Static support for the first OS seed

Add `--bootstrap-libgcc` to a new `--kernel` build when no EmberBSD base
sysroot exists. First install the selected target's headers from a clean
EmberBSD source commit with the fork's native host tools. Use a separate
`DESTDIR`, the selected `MACHINE`/`MACHINE_ARCH`, and sequential `obj`,
`do-distrib-dirs` and `includes` targets. These stages do not compile target
libraries. Preserve the installed relative `usr/include/machine` link.
Do not copy headers from an upstream NetBSD sysroot.

On a host without an EmberBSD toolchain, build these host tools with the
fork's in-tree defaults. Do not set `TOOLCHAIN_MISSING=yes` for this
`TOOLDIR`: `build.sh` then requires an existing `EXTERNAL_TOOLCHAIN`.
The same `TOOLDIR` supplies `nbgmake` to this recipe and to `host-math.py`.
Use a separate object directory:

```sh
cd /absolute/EmberBSD
sh build.sh -U -u -j4 -m evbarm -a aarch64 -O /absolute/os-build/objects \
    -T /absolute/os-build/tools -D /absolute/header-sysroot \
    -V MAKECONF=/dev/null -V HOST_CC=cc -V HOST_CXX=c++ \
    -V BUILDINFO=EmberBSD:FULL_40_CHARACTER_EMBERBSD_SOURCE_COMMIT tools
make=/absolute/os-build/tools/bin/nbmake-evbarm
"$make" DESTDIR=/absolute/header-sysroot obj
"$make" DESTDIR=/absolute/header-sysroot do-distrib-dirs
"$make" DESTDIR=/absolute/header-sysroot includes
```

On 2026-10-23, these commands produced the AArch64 header sysroot on macOS
arm64. The `--bootstrap-libgcc` build below accepted it.

Supply this header sysroot immediately after the GCC archive. Set
`EMBERBSD_SYSROOT_SOURCE` to its verified full EmberBSD source commit.
`EMBERBSD_SYSROOT_PROVENANCE` can name a file with the source revision,
header installation commands and hashes. This follows the existing
[runtime bootstrap provenance convention](../bootstrap/README.md).
Ports records the caller's verified source claim and optional provenance
file hash; it does not independently reconstruct the header installation.
Keep all options before the positional inputs:

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=4 \
    EMBERBSD_SYSROOT_SOURCE=FULL_40_CHARACTER_EMBERBSD_SOURCE_COMMIT \
    EMBERBSD_SYSROOT_PROVENANCE=/absolute/header-install-receipt.json \
    python3 -B profiles/development-toolchain/cross/build.py \
    --kernel --bootstrap-libgcc --target aarch64 \
    /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz /absolute/header-sysroot \
    /absolute/os-build/tools /absolute/host-math/prefix /absolute/new-gcc-seed
```

The option requires `--kernel`. Application mode, duplicate options and
unsupported targets fail before work is created. Without the option, kernel
mode remains frontend-only. The header sysroot must contain the original
`stddef.h`, `stdio.h`, `sys/types.h`, `sys/cdefs.h`, `sys/common_ansi.h` and
the selected `machine/ansi.h`. AArch64 also requires `arm/ansi.h`. It must
not contain compiled libraries or objects. The builder records the complete
header sysroot inventory in `bootstrap-headers.json`. Escaping links,
a missing source claim, a mismatched machine link or changed inputs fail.

The new build first installs the audited kernel frontends. It then runs
upstream `all-target-libgcc` and `install-target-libgcc` in that build tree.
The target tools come from the same audited prefix. The frontend must retain
`inhibit_libc=true`, shared support disabled and the single thread model.
The target library configuration must also disable shared support. This
build requires no target libc. GCC's NetBSD `stddef.h` includes
`machine/ansi.h` even in this mode, so actual target ABI headers are required.
The compiler uses `--with-sysroot=HEADERS` together with `--without-headers`.
The producer explicitly sets GCC's configure input `inhibit_libc=true` and
checks the generated Makefile: with a sysroot, GCC does not infer this value.
It retains upstream libgcov, static support targets and all diagnostic checks.

The builder checks all installed `libgcc.a` members and the four required
GCC CRT objects for the selected target ELF architecture. It also checks any
installed `libgcov.a`, `libgcc_eh.a`, `crtbeginT.o` and `crtfastmath.o`.
The compiler must select those exact files through its normal search paths.
An empty archive, shared libgcc or C++ runtime fails the check. The separate
`bootstrap-libgcc.json` records configuration and artifact hashes with the
scope `static-libgcc-bootstrap-only`. It is not a runtime bootstrap success
marker or a POSIX runtime provider. The receipt includes the header input
record hash. The complete header snapshot and optional provenance file must
remain unchanged through compiler and static support construction.

Use this prefix to compile the first seed from the selected EmberBSD sources:
OS CRT, libc, libm, pthread and the loader, using the installed headers.
Keep the seed's source
commit, build commands and file hashes. Do not select
`EMBER_EXTERNAL_GCC_RUNTIME` for this stage; that adapter requires the full
accepted POSIX runtime. The kernel compiler's own prefix supplies its static
libgcc and GCC CRT. The OS supplies `crt0.o`, `crti.o` and `crtn.o`.

Use the existing host `TOOLDIR` and a new object directory. Set
`TOOLCHAIN_MISSING=yes` and point `EXTERNAL_TOOLCHAIN` at the kernel compiler
prefix. Disable C++, compatibility libraries and optional components. Use
`build.sh` only to create a make wrapper. Then install the headers and build
the five seed directories in sequence:

```sh
cd /absolute/EmberBSD
set --
for v in TOOLCHAIN_MISSING=yes \
    EXTERNAL_TOOLCHAIN=/absolute/new-gcc-seed/toolchain \
    MKGCCCMDS=no MKCOMPAT=no MKCXX=no MKDEBUG=no MKDEBUGLIB=no MKX11=no \
    MKLLVM=no MKLLVMRT=no MKLIBCXX=no MKKMOD=no MKGDB=no MKBINUTILS=no \
    MKATF=no MKKYUA=no MKMAN=no MKDOC=no MKINFO=no MKHTML=no MKLINT=no \
    MKPROFILE=no MKCVS=no MKGROFF=no MKRUMP=no MAKECONF=/dev/null \
    HOST_CC=cc HOST_CXX=c++ \
    BUILDINFO=EmberBSD:FULL_40_CHARACTER_EMBERBSD_SOURCE_COMMIT; do
    set -- "$@" -V "$v"
done
sh build.sh -U -u -j4 -m evbarm -a aarch64 -O /absolute/seed-objects \
    -T /absolute/os-build/tools -D /absolute/new-seed \
    -w /absolute/seed-make "$@" makewrapper
make=/absolute/seed-make
"$make" obj
"$make" do-distrib-dirs
"$make" includes
for d in lib/csu lib/libc lib/libm lib/libpthread libexec/ld.elf_so; do
    "$make" -C "/absolute/EmberBSD/$d" -j4 dependall
    "$make" -C "/absolute/EmberBSD/$d" install
done
```

The seed then contains the OS CRT objects, `libc`, `libm`, `libpthread`,
`/libexec/ld.elf_so` and the relative `usr/libexec/ld.elf_so` link. On
2026-10-23, these commands produced the AArch64 seed on macOS arm64. The
runtime bootstrap below accepted it.

Next run the normal [runtime bootstrap](../bootstrap/README.md) against that
seed. Build the application compiler against a separate union of the seed
and accepted POSIX runtime. Rebuild the final SDK sysroot with that
application compiler. Static bootstrap support must not replace any of those
later stages. Controller fixtures validate this option and its artifact
guards; a complete first-seed build and target execution remain separate checks.

On 2026-10-11, the public recipe built GCC16.2 with host GCC16.2 on Debian
x86_64 Linux, passed its installed split-DWARF contract, and cross-built the
OS revision `d472eb8fecc3ff70b6aa231888b301414985845c`: EMBER64 kernel and image,
four modules and three board DTBs. The OS wrapper's portable contracts passed
with GCC16. Boot, the four native contracts and Linux-hosted application-mode
runtime acceptance remain unverified.

The only `libatomic` is compiler-rt's shared `clang_rt.atomic`
([lang/compiler-rt](../../../pkgsrc/lang/compiler-rt/Makefile)), linked as
`-latomic`; no GCC libatomic is packaged.

## Host controller checks

```sh
python3 -B profiles/development-toolchain/tests/python/controllers-test.py
python3 -B profiles/development-toolchain/tests/python/environment-test.py
python3 -B profiles/development-toolchain/tests/python/host-capture-test.py
python3 -B profiles/development-toolchain/cross/tests/lto-binutils.py \
    /absolute/gcc-cross/toolchain /absolute/new-lto-check
python3 -B profiles/development-toolchain/cross/tests/plugin-needed-warnings.py \
    --target amd64 /absolute/gcc-cross-amd64/toolchain /absolute/sysroot-amd64 \
    /absolute/new-plugin-check --sdk-source /absolute/EmberBSD-SDK
sh profiles/development-toolchain/tests/prepare.sh /absolute/new-pkgsrc-test
```

Host query capture uses SDK producer stream and input API1. It owns each
query session, including compiler preprocessing. It keeps nonzero status
and exact output bytes within the limits. It refuses stdout above 16 MiB,
stderr above 1 MiB, or a query above 120 seconds. An unproven session drain
raises `ProcessOwnershipError`; the caller must quarantine its work and
retain its input leases until explicit recovery.

The environment contract executes real captured and logged children. It checks
Darwin-only SDK inheritance, explicit overrides and malformed paths. On Darwin,
it also compiles, links and executes a C probe with the selected SDK and GCC16.
These checks retain the normal process ownership guard.

The controller fixtures check both triplets, the two compiler modes, source
and tool identities, native metadata tools, runtime selection and interrupted
build state. They use deliberate invalid inputs and independent expected
configure arguments. They do not establish a real GCC build. The optional
LTO probe uses the actual selected compiler and Binutils. It does not execute
target code. Keep compile, package, target and board acceptance separate.

## Compile here, execute on EmberBSD

```sh
/absolute/native-ports-prefix/bin/python3.15 -B profiles/development-toolchain/cross/compile-tests.py \
    --sdk-source /absolute/EmberBSD-SDK --compiler-family clang \
    --host-prefix /absolute/native-ports-prefix \
    /absolute/target-clang-prefix /absolute/sysroot /absolute/new-tests
```

The SDK API2 helper selects the target compiler commands and the completed
sysroot's matching Clang runtime. Pass `--target amd64` for an amd64 prefix and
sysroot. Use `--compiler-family gcc` only for an explicitly selected GCC16
target runtime; that route retains the existing GCC16 prefix checks. The output
includes `compiler-family.txt`, `compiler-identity.json`, `runtime-files.tsv`,
`sysroot-identity.json`, `source-sha256.tsv`, `target.txt` and the
target-option helper. The sysroot identity records compile inputs only and
explicitly leaves execution acceptance unrun. Keep these data receipts with
the test programs.

This reuses the native C11 atomics/TLS and C++20 DSO test sources. It compiles
C with and without LTO, and C++ with threads, TLS, strings and exceptions
crossing a shared-library boundary. A floating constant-evaluation regression
includes `_Float32` limits and target long-double exponentiation.
It checks dynamic dependencies for host path leakage. The guest runner uses
target shell/base utilities and verifies loaded runtime paths and hashes from
the non-executable runtime data receipt. It does not install host development
tools or override the target loader environment. Compilation alone is not
runtime acceptance.

Run the SDK-selection and guest runtime-checker fixtures with:

```sh
/absolute/native-ports-prefix/bin/python3.15 -B profiles/development-toolchain/cross/tests/target-toolchain.py \
    --sdk-source /absolute/EmberBSD-SDK
```

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
and all nine artifact hashes passed; see the [OS-owned evidence](https://github.com/oxtech-ember/EmberBSD/blob/main/tools/docs/cross-build.md#linux-gcc16).
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

Host compiler SDK selection can be passed through `HOST_CPPFLAGS` and
`HOST_LDFLAGS`. The cross builder propagates the former to recursive host
libraries and C/C++ rules, including libcody. For example, with an explicit
Darwin SDK use `-isysroot /absolute/MacOSX.sdk` in both variables. These flags
select host build inputs; target headers still come from the selected sysroot.
