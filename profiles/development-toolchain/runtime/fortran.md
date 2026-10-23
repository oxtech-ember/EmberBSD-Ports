# Separate GCC16 Fortran runtime and SDK data

This source checkpoint adds target Fortran libraries to the accepted
`gcc16-runtime-16.2.0nb6` ABI. It does not replace that package or a running
compiler generation. Use the same GCC16.2 archive and full prepared GCC recipe.
Use a new compiler generation with a completed real Fortran capability receipt.
The producer configures only the upstream PIC `libbacktrace` convenience
library and `libgfortran`. On amd64 it also builds required `libquadmath`.
It uses their real make/install rules.
The shared `fortran_target.py` contract selects the component plan, stage
payload and cross SDK alias checks. GCC16.2 AArch64 uses IEEE binary128
`long double` and does not register `__float128`. Upstream libquadmath requires
that distinct type. AArch64 therefore has no libquadmath component or payload.
This decision does not depend on file absence. amd64 still requires both libraries.
Unknown targets fail. Neither target disables upstream Fortran math support.
This AI-assisted target contract follows the upstream [floating type contract](https://gcc.gnu.org/onlinedocs/gcc/Floating-Types.html)
and the architecture selection in [OpenBSD GCC16](https://github.com/openbsd/ports/blob/master/lang/gcc/16/Makefile).
GCC16.2 `libquadmath/configure.ac` tests `__float128`.
`libgfortran/acinclude.m4` uses quadmath only with usable `_Float128` and `__float128`.
The Fortran type mapper can use binary128 `long double` without libquadmath.

It does not run the top-level compiler or C/C++ runtime targets.

The CLI uses Python 3.15 stdlib and explicit SDK API1 sources. The SDK must
provide `ContextLocks(shared=True)` and owned producer stream/input API1.
Set an audited PATH with GNU make, M4, awk, sed, shell, Texinfo and install.
The producer hashes the selected executables and records every component argv.
It sets `GFORTRAN`, `FC` and `F77` to the same target command. Upstream
`libgfortran` resets `FC` from `GFORTRAN` before its compiler checks.
No target executable runs on the host. The selected upstream component rules do
not compile a native helper with `CC_FOR_BUILD`. Libquadmath only forwards
that variable in recursive make flags. This is not native host-link acceptance.
If a future upstream rule uses it, verify its real host SDK before that link.
The producer retains the authenticated nb6 SDK thread header inputs.
The raw C thread interface comes from the accepted libgcc build provider.
It verifies the POSIX rule and equal raw sources in both accepted builds.
Installed C++ thread headers have upstream namespace transformations.
They are not substituted for the raw C provider.
The producer does not create a replacement header or rebuild target libgcc.
The stage requires upstream Libtool's `0755` mode for regular `.la` metadata.
Libtool uses `INSTALL` for those files. Other SDK data retains mode `0644`.
The verifier does not change installed modes.
It reads literal `.la` assignments with shell quoting but does not execute them.
It ignores full comment lines. It rejects substitutions, unquoted shell operators
and malformed assignments. Quoted punctuation remains literal data.
The new work maps its upstream `build/gcc` include role to the accepted
frontend generation. Its target `libgcc` include role maps to the accepted
base runtime build. Both providers stay shared-locked. The producer checks
their source version, target, required generated headers and bounded header
hashes before and after use. Existing capability and base checks require the
same GCC16.2 archive and full prepared recipe. It creates only these new-work
directory links.
It does not create empty include directories or change warning policy.

```sh
HOST_CC=gcc-16 CROSS_JOBS=12 GNU_MAKE=/absolute/host/bin/gmake \
python3.15 -B profiles/development-toolchain/bootstrap/build-fortran-runtime.py \
    --sdk-source /absolute/EmberBSD-SDK --lock-root /absolute/workspace/obj \
    --host-prefix /absolute/native-pkgsrc --target amd64 \
    /absolute/prepared-pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/new-gcc-generation/toolchain /absolute/sysroot \
    /absolute/accepted-base-runtime-work /absolute/workspace/obj/new-fortran-runtime
```

Add `--check` to inspect the real prerequisites and print the command plan.
That mode reads the selected SDK and compiler under shared physical leases.
The cross policy runs after final language option selection. This includes
FFTW, which adds its default Fortran language after its first prefs include.
It does not create a runtime work directory or run configure/make.
The selected sysroot, source roots, frontend, archive, native package prefix
and accepted base runtime stay shared-locked. The exact new work stays
exclusively locked. An ordinary failure preserves work and releases leases
after producer drainage. Typed ownership uncertainty quarantines owned work
and retains the leases in HOLD. Audit the producer session before recovery.
INT, TERM and HUP do not release a typed HOLD. SIGKILL and host failure are
outside this cooperative guarantee. Never retry failed work automatically.
Do not change an external reader registry from this command.

The producer fingerprints the complete base outside `usr/pkg`, its headers,
selected compiler support, accepted base runtime stage, tools and sources.
It compares them before publishing `fortran-stage.json`. A base inventory is
an integrity check. The operator must first verify its source-built origin.
The receipt binds the base build manifest and the authenticated GCC runtime.
A fresh inventory does not establish historical source provenance.

`lang/gcc16-fortran-runtime` owns only target versioned Fortran/quadmath DSOs,
their aliases and original component licenses. It depends exactly on nb6.
`lang/gcc16-fortran-devel` owns the upstream headers, intrinsic modules,
specs, static support and unversioned aliases. The verifier requires all three
IEEE modules and upstream single-image coarray support. amd64 also requires
both quadmath headers, its static library and matching shared alias. AArch64
rejects quadmath payloads and DSO dependencies. It depends exactly on both
runtime providers. Install the latter normally into the development sysroot.
Do not copy files into the compiler prefix. Do not transfer SDK data to a
runtime-only device. No SDK transfer schema fields are added.

Set `GCC16_FORTRAN_PYTHON`, `EMBERBSD_SDK_SOURCE`, `GCC16_FORTRAN_WORK` and
`GCC16_FORTRAN_ARCHIVE` for ordinary package builds. The verifier rejects
wrong target ELF, SONAME, RELRO, closure, runtime paths, escaped links,
overlapping role payloads, host paths in link metadata and changed inputs.
Keep the external work and archive for readback and reproducibility.

The [consumer fixture](../../../probes/gcc16-fortran/README.md) establishes the
next link/runtime gate. Source and synthetic controls do not establish real
component builds, package acceptance, FFTW, runtime execution or promotion.

Run the bounded source controls with explicit SDK and prepared pkgsrc sources.
Create the result parent first. Each framework result path must be new.

```sh
python3.15 -B profiles/development-toolchain/runtime/tests/fortran-commands-test.py \
    --gcc-source /absolute/audited-gcc-source \
    --bmake /absolute/host/bin/bmake --sdk-source /absolute/EmberBSD-SDK
python3.15 -B profiles/development-toolchain/runtime/tests/fortran-stage-test.py \
    --ports-source /absolute/EmberBSD-Ports --sdk-source /absolute/EmberBSD-SDK
python3.15 -B profiles/development-toolchain/runtime/tests/fortran-producer-test.py \
    --ports-source /absolute/EmberBSD-Ports --sdk-source /absolute/EmberBSD-SDK \
    --configured-libgfortran /absolute/retained-libgfortran-build \
    --gnu-make /absolute/host/bin/gmake
python3.15 -B profiles/development-toolchain/runtime/tests/fortran-framework-test.py \
    --sdk-source /absolute/EmberBSD-SDK --bmake /absolute/host/bin/bmake \
    --pkg-admin /absolute/host/sbin/pkg_admin \
    --pkgsrc-source /absolute/prepared-pkgsrc /absolute/new-framework-result
```

The command controls run the exact `FC="$GFORTRAN"` assignment from the
audited upstream `configure.ac` and generated `configure`. They demonstrate
the lost command without `GFORTRAN` and exact target argv with it. They do
not run configure or a compiler.

The architecture controls retain required quadmath on amd64. They accept
AArch64 gfortran-only stage data and reject quadmath payloads, dependencies
and link metadata there. Isolated BSD make fragments use the same target
contract to require the correct SDK aliases. They do not bootstrap pkgsrc.
The ELF fixtures validate the new stage parser and role guards. Their base
runtime validator is mocked in receipt mutation controls. The producer controls
inject failures before any real preflight, compiler or extractor call. They
exercise real lease conflicts and owned-work quarantine. Synthetic generated
header providers test the new-work role links and refusal guards. The optional
configured Makefile control runs its exact include flag fragment with GNU make.
It keeps every flag and resolves the two missing directories after binding. The framework controls
apply the real patch with zero fuzz and run BSD make on isolated source
fragments. The package-pattern controls use the real `pkg_admin pmatch` command
without a package database. They reject adjacent ABI revisions. Their native compiler paths are fixtures. These checks do not start
normal pkgsrc metadata, dependency installation or actual compiler queries.
The separate real-function HOLD control injects diagnostic failure only after
leases are open. It checks normal stderr, closed fd2 and EIO. The protected
function retains real shared SDK/native/generation/prefix and exclusive work
leases under TERM, INT and HUP. Removing only the diagnostic guard reproduces
premature release. Every fixture session is drained through the SDK.

```sh
python3.15 -B profiles/development-toolchain/runtime/tests/fortran-hold-test.py \
    --candidate-source /absolute/EmberBSD-Ports \
    --ports-source /absolute/EmberBSD-Ports --sdk-source /absolute/EmberBSD-SDK \
    --new-work /absolute/new-hold-fixtures
```

These checks do not establish the real native Libtool or target link/runtime
contracts. Full package metadata and runtime acceptance remain separate.

The C interoperability main also has bounded amd64 analysis with real GCC16
predefines and source-built EmberBSD headers. GCC16 `-fanalyzer` and Clang21
Static Analyzer report no findings for that TU. GCC syntax-only parsing is
separate from its analyzer pass. Cppcheck2.22 completes the actual
GCC-preprocessed configuration and reports three inherited unused inline
header functions. Its raw nonzero status is retained. Direct header parsing
stops at the compiler builtin `__has_builtin`; that route is not completed.
These results do not analyze the Fortran callee, runtime library or linked
consumer. They do not establish a memory-checker or runtime pass.
