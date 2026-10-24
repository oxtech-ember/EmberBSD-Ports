# Common development toolchain (candidate)

The [GNU sed multibyte repair](gsed.md) clears opaque conversion states in
four production paths. It fixes sed state handling with GCC15+ on NetBSD without
forcing C locale behavior or weakening patch checksums. Native GCC16 runtime
and upstream checks are recorded separately from package acceptance.

This profile builds GCC 16.2.0 for native EmberBSD/NetBSD 11 AArch64.
The candidate package builds in the AArch64 VM and runs there and on physical
Orange Pi Zero 3W, passing C11/C++20 thread, TLS, shared-library and runtime-identity probes. It is the
compiler foundation for a reproducible distribution development environment.
The common build-tools MAKECONF selects it for new package consumers after
bootstrap; actual native pkgsrc wrapper and installed-consumer checks pass on
Zero 3W. Full upstream tests, shared consumer migration and image integration
remain gates. Reversible development defaults select installed nb1 for fresh
login/SSH sessions and ordinary pkgsrc builds on the checked Zero 3W board;
base compiler files remain intact.

On the AArch64 NetBSD 11 VM, the native prerequisites are now validated:
MPC 1.4.1 (75 tests), Texinfo 7.3 (required XS plus Info/HTML output),
Expect 5.45.4nb1 (29 tests and a PTY roundtrip), and DejaGNU 1.6.3
(604 expected passes). Perl 5.44.0 and its two ABI-bound JSON/Parse::Yapp
modules passed their tests and affected consumer checks after a coordinated
replacement. These results do not establish GCC or common C++ ABI acceptance.
The [bounded native build helper](tools/README.md) preserves build exit status
and checks guest scratch reserves for the long package build.

A [host cross-compiler recipe](cross/README.md) also builds GCC 16.2 on
Apple Silicon macOS. Cross-built C11/C++20 programs pass on Zero 3W with
its installed GCC16 runtime. This separates compilation from target
execution; it does not yet cross-build installable pkgsrc packages.
Its `--kernel` mode prepares the same patched compiler frontends without a
userland sysroot. Application mode retains the target GCC16 headers/runtime
requirement; kernel compilation and boot need their own OS acceptance.
The cross entry points also accept `--target amd64` (`x86_64--netbsd`).
The real amd64 application compiler builds on macOS arm64 with POSIX threads
and passes compiler and split-DWARF checks. The runtime-only nb6 package passes
EmberBSD 11.0 amd64 installation, removal, exact package-list restoration
and reinstallation. Installed C11/C++20, TLS, DSO, OpenMP and generic atomic
contracts pass; see the [runtime acceptance](runtime/README.md#amd64-installed-acceptance).
The target retains its existing base. A new source-built base, a complete
image and Plasma remain separate acceptance gates.

The separate [firmware frontend](cross/firmware.md) requires
`--target arm-none-eabi`. It builds only the C frontend and Binutils for
freestanding Cortex-M4 Thumb objects. It does not add an application sysroot,
a target runtime or ARM userland support. Real firmware acceptance is separate.

The [GDB 18.1nb1 native debugger](gdb/README.md) also cross-builds on macOS.
It reads split and standard supplementary DWARF in the AArch64 VM and
passes live breakpoints, locals, FP registers and signal-frame unwinding.
Its DWARF2–5/32–64 matrix and general entry-value expressions pass with the
installed package; [entry-state tests](gdb/entry-value.md) distinguish recovered
values from unavailable history.
Ports carries the current native backend and dependency compatibility
repairs. The shared layer has one current `devel/gdb` package recipe
(`pkgsrc/devel/gdb`);
the [package guide](gdb/package.md) connects it to the OS-owned development image.

## Source and preparation

The base is pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`
(`pkgsrc-2026Q3`). Apply the original NetBSD update
[`823a3b483b7ffeb73973f911458d6ba22c74efc4`](https://github.com/NetBSD/pkgsrc/commit/823a3b483b7ffeb73973f911458d6ba22c74efc4)
to `gcc16`, `gcc16-libs`, and `gcc16-libjit` together. This imports the
16.2.0 version and archive checksums without advancing unrelated packages.
The full original update is preserved in `patches/pkgsrc-gcc16.2.patch`.
Original archive and patch URLs/SHA256 are in `sources.tsv`; GCC's SHA512
and BLAKE2s remain in the resulting pkgsrc `distinfo`.

Exports use the pinned upstream `devel/gmake` and `sysutils/dtc` recipes.
The board-firmware toolchain (dtc, `aarch64-none-elf-binutils` and
`aarch64-none-elf-gcc` with GCC16 and Binutils 2.47) is an incomplete
[probe](../../probes/firmware-toolchain/README.md). The export does not
include it.

The [bootstrap prerequisite delta](prerequisites.md) prepares MPFR 4.2.2,
MPC 1.4.1 and Texinfo 7.3, with verified archives and portability patches.
MPFR 4.2.2, MPC arithmetic tests and the unchanged GCC package's dependency
checks pass on Zero 3W; see the [native validation](native-validation.md).
Texinfo's Perl XS dependency requires the pinned Perl 5.44.0 package and
rebuild of any existing Perl modules before replacing an earlier Perl ABI.

The local AI-assisted `strict-tests.patch` is not submitted upstream. It
preserves failed `make check` status, corrects the historical SONAME comment,
and removes the ISL source patch because this profile does not extract ISL.
Do not enable Graphite in this exported profile. No compiler source or
runtime ABI is renamed. Existing pkgsrc patches retain their authorship.
GCC and its runtime retain upstream licenses and GCC Runtime Library Exception;
the probe code is BSD-2-Clause.

The [C++ modules allocation repair](modules-portability.md) prepares
`gcc16-16.2.0nb1` with the accepted upstream `ENOTSUP` fix and a local NetBSD
`EOPNOTSUPP` extension. Production-function source regressions and private
frontend module export/import/link/run pass on Zero 3W A733. Normal package
creation/file checks and final installation pass; the installed driver passes
the same module gates without `-B`. The updated common-consumer fixture
passes through the durable system pkgsrc configuration on that board.

The [NetBSD numeric-locale repair](locale.md) prepares the shared GCC16
header and library to avoid process-wide locale changes during C++ numeric
conversion. Native checks and real AArch64 source-object execution preserve
numeric behavior and repair the concurrent locale change. The ordinary
[runtime-only nb3 package](runtime/README.md#aarch64-installed-acceptance)
passes installed SDK and EmberBSD VM upgrade checks, including plain/LTO
locale, threads, OpenMP, atomics and the rebuilt Skia contract. Its removal
and reinstallation, broader consumer migration and image integration remain gates.

The [NetBSD cross math capability repair](cross-math.md) uses real declaration
and libm link probes for the C++ standard modules. It introduced compiler nb3,
libs nb4 and runtime-only nb4. Source/module compilation
and installed package/runtime acceptance are separate checks.
The [NetBSD cross TLS repair](cross-tls.md) detects thread-local storage in
cross libstdc++ configuration, as native builds do. It selects the native
`std::call_once` ABI with `std::__once_call` and advances the recipes to
compiler nb4, libs nb5 and runtime-only nb5. Rebuild consumers of the earlier
non-TLS runtime; see [compatibility](cross-tls.md#compatibility).
The runtime verifier checks actual dynamic TLS exports. A Debian-hosted
AArch64 regression confirms the configure probe and original C++ objects.
The [macOS AArch64 host delta](gcc-darwin-host.md) builds the native GCC16
for build-host programs from the upstream Darwin port.

The [cross-native delta](cross-native.md) builds the target compiler package
on the development host. It advances the recipes to compiler nb5 and libs nb6.
In a runtime-provider closure, this compiler layers over `gcc16-runtime` nb6.

The [TSVC portability backport](testsuite-portability.md) applies GCC's accepted
NetBSD allocator fix without changing the compiler or runtime. The exported
recipe keeps every vectorization assertion and the strict test exit status.

```sh
git submodule update --init --depth 1 upstream/pkgsrc
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc
```

The destination must be new. Existing exports are never changed in place.
The same export has the [common build tools](../common-build-tools/README.md)
Python/Meson recipes; their native package acceptance is separate. Their MAKECONF selects the prepared GCC16 package
for new consumers; keep it out of this native-GCC bootstrap closure.
The exported `EMBERBSD-DEVELOPMENT-MK.CONF` selects C/C++ only, external
GMP/MPFR/MPC, one worker, `-O2` without debug information, and the compiler's
own libgcc. Graphite, NLS, Fortran, Cobol, Go, and Objective-C are disabled.
These are language/optional-feature limits, not missing basic C/C++ semantics.

## Native package build boundary

Build only a committed Ports revision. Capture that commit, the pkgsrc pin,
private MAKECONF, dependency versions, configure output, logs, and package hash.
The intended repaired package is `gcc16-16.2.0nb1`, installed with pkg_tools at the recipe's
standard `/usr/pkg/gcc16` prefix. Base files are never overwritten.
Use pkgsrc's DESTDIR/package staging; do not relocate GCC after configuration.

The build's private MAKECONF includes the exported profile, sets WRKOBJDIR,
DISTDIR and PACKAGES to scratch storage, and keeps LOCALBASE `/usr/pkg`.
First use the base compiler to build the candidate. Do not set GCC_REQD=16
while building its own bootstrap dependencies. Native tools include gmake,
GNU sed, texinfo >=7, Perl, pkg_tools, cwrappers and digest. Math dependencies
are GMP, MPFR, and MPC (`math/mpcomplex`); the recipe also needs libxml2.
DejaGNU with Expect/Tcl is required for upstream tests. Resolve full pkgsrc
dependencies before starting; this list is not a substitute for that check.

The upstream recipe disables bootstrap on all NetBSD hosts because GCC 16.1
stage2/stage3 comparison failed on x86_64. This profile retains that choice
for the initial resource-limited candidate. It does not imply the same failure
on AArch64 or prove self-hosting. A subsequent AArch64 self-build and comparison
investigation is a distribution gate, not something to hide with `|| true`.
The initial compiler uses base binutils; the common development profile must
subsequently select current binutils and repeat generated-code tests.

Measured source footprint: 107,200,820-byte archive, about 1.3 GiB extracted;
the full prepared pkgsrc tree is about 0.8 GiB. Budget 4–6 GiB for objects,
2 GiB for staging/install/package overlap, 1 GiB for test/temp/distfiles,
and at least 1 GiB reserve. Provision 16 GiB scratch; 12 GiB is a tight
estimate, not a measured peak or sufficient room for a three-stage bootstrap.
Use one worker on a 4 GiB guest. Drain other compiler jobs first; inspect
memory and free space throughout. No storage deletion or swap setup is implicit.

## Runtime and consumer repair

The observed base compiler is GCC 12.5.0nb3 with `libstdc++.so.9` and
`libgcc_s.so.1`. Qt 6.11.1, ICU, and LLVM 21.1.8 currently load that runtime.
The pkgsrc GCC16 recipe intentionally retains its own `libstdc++.so.7`.
Changing its SONAME to 9 does not make the ABIs identical. Never add a SONAME
symlink, use LD_LIBRARY_PATH to conceal resolution, or mix the two C++ runtimes
in one process as an accepted configuration.

Build a coherent new C++ closure using GCC16: shared-runtime dependencies
(including ICU and double-conversion), Qt, KF, LLVM and desktop consumers.
The coordinated consumer targets are Qt 6.12.0, KF 6.30.0, and LLVM 23.1.2;
these are rebuild targets, not the currently installed versions above.
Inventory every transitive DSO before adopting it; C interfaces alone do not
prove that a dependency has no hidden C++ runtime. Fix source incompatibilities
in Ports, then rebuild and retest their consumers with the same compiler.
Existing current GUI builds finish with the original compiler. After that
boundary, rebuilt packages replace the corresponding installed packages as a
coordinated set with retained rollback packages. This repair is required work,
not an indefinite exception allowing old runtime consumers in new builds.

The base compiler and its runtime temporarily remain for bootstrap, recovery,
and already-running old programs. Their removal gate is a validated base OS
toolchain migration plus rebuild of remaining base consumers. They are not an
application-specific alternative, and must not be the new image's user-facing
default development tools.

## Acceptance

After the package installation is explicitly scheduled, use an ordinary clean
loader environment and run:

```sh
sh profiles/development-toolchain/tests/run.sh /usr/pkg/gcc16 /absolute/new-check
sh profiles/development-toolchain/tests/qt-consumer.sh /usr/pkg/gcc16 \
  /usr/pkg/qt6/lib/pkgconfig /absolute/new-qt-check
```

The first check compiles and runs C11 atomics, pthreads, C/C++ TLS, C++20,
cross-DSO strings and exception cleanup. It records DT_NEEDED and `ldd`, then
uses the actual process link map to require exactly one libstdc++ and libgcc_s,
both matching this compiler's reported runtime files under its own prefix.
For libgcc, compare the actual `libgcc_s.so.1` DSO: upstream intentionally
installs `libgcc_s.so` as a GNU linker script, not an ELF-library symlink.
The Qt check exchanges real strings with QtCore and repeats runtime identity
checks. It must fail on an unresolved old/new runtime mixture. Also audit LLVM's
dynamic closure and run an LLVM consumer after its rebuild; Qt success cannot
prove LLVM compatibility.

Run upstream tests through the strict recipe and retain the true exit status
and `.sum`/`.log` files. Failed checks need classification and concrete fixes;
a generated summary or successful `--version` is not acceptance.

For new pkgsrc consumers, select GCC16 through the common build MAKECONF
by including `EMBERBSD-COMMON-TOOLS-MK.CONF` after the bootstrap package exists.
It uses `GCC_REQD+=16.2`, the major.minor floor understood by pinned pkgsrc;
the package version remains 16.2.0. It retains the complete `always-libgcc`
package as a full dependency, without adding a separate `gcc16-libs` provider.
For CMake/Meson, use explicit compiler paths in fresh build directories;
cached compiler identities cannot be changed by modifying PATH alone.
Verify generated compile commands and runtime mappings before selecting
the toolchain for all new builds. Preserve the previous selection for rollback.

## Distribution integration

The inspected OS checkout currently builds kernels using NetBSD 11's native
tools and documents official NetBSD 11 userland; it has no complete public
image assembler that installs this development profile. Package installation
alone therefore does not satisfy current-image release acceptance.

The image build must consume a pinned Ports commit, a recorded package set
and hashes, and one explicit common compiler/tool selection. Install the
validated packages into the image through pkg_tools, configure user-facing
`cc`, `c++`, `gcc`, and `g++` selection without overwriting package/base files,
and repeat the compiler/Qt/LLVM checks in a fresh boot of that image. Record
base bootstrap exceptions separately. Keep a tested reversal of selection.

Additional current binutils, LLVM/Clang, CMake, Meson, pkgconf, Libtool, Perl,
Python, Ruby, Go, and TinyGo recipes join this profile through reviewed Ports
deltas. They must share the same runtime policy and image manifest; stale
installed versions are not the release target. Upstream Python requirements
remain visible; project-owned build/test helpers here do not use Python.
TinyGo's LLVM compatibility needs validation and source repair against the
common LLVM version; do not silently install another LLVM for that consumer.

## Verified scope (2026-10-07)

GCC 16.2.0 built and packaged on the AArch64 NetBSD 11 VM with one worker,
base GCC 12.5 and base binutils. Native pkgsrc check-files passed; the installed
candidate's 1,633 files passed pkg_admin verification. The package build took
1,303 seconds with a reported peak RSS of 995,952 KiB on a 4 GiB guest without swap.
The recipe retains `--disable-bootstrap`; no three-stage bootstrap is claimed.

The installed candidate passed C11 atomics/pthreads/TLS and C++20 shared-DSO
string exchange, exception cleanup, threads and TLS. The actual process map
contains one libstdc++ and one libgcc_s from `/usr/pkg/gcc16`. Base compiler
and runtime file hashes stayed unchanged in the original check. The later
[board development-default gate](../common-build-tools/development-defaults.md)
selects installed repaired nb1 in fresh sessions and ordinary pkgsrc builds
with verified reversal; it does not replace the base compiler.
The installed old Qt 6.11 closure correctly fails the same identity check:
it loads both candidate libstdc++.7 and base libstdc++.9. Its Qt/ICU/LLVM
consumer rebuild remains required; a working isolated C++ probe cannot accept
that mixed process. The completed strict upstream suite reports real failures;
the complete profile has not passed its acceptance gate.

The current AArch64 VM kernel starts processes with flush-to-zero and default
NaN modes. A separate native probe reproduces loss of subnormal results and
NaN payloads with both base GCC 12.5 and this candidate. Process-local IEEE
mode produces the expected values. The [EmberBSD kernel correction](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/aarch64-fp-state.md)
passes production contracts and native object compilation; its boot/runtime
acceptance remains required. Compiler flags must not conceal the failure. Nested-function stack
trampolines also fail with both compilers on this platform. GCC16's current
recipe does not build a NetBSD sanitizer runtime, and the ASan suite stops
during runtime initialization. An unchanged upstream atomic LTO test exposed
a separate libc CAS1/CAS2 defect: the helper compares untrimmed expected
register bits against a zero-extended narrow load. The failing executable
uses the libc helper; the passing variant contains a normalizing libgcc
helper. The [OS CAS repair](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/aarch64-outlined-cas.md)
passes 850 native production checks and that unchanged upstream test linked
explicitly to the corrected objects. On physical Zero 3W the complete corrected
libc is installed, and the original atomic/binary128 LTO cases pass with and
without the linker plugin through normal system-library resolution. The VM
libc remains unchanged. Other LTO and
target/configuration failures remain under investigation. These findings do not invalidate the
completed package build or justify rebuilding the same sources unchanged.
Preserve unmodified test results; acceptance of the complete shared consumer
closure and user-facing image defaults remain deferred.

Source validation covers pinned archives, the upstream update, all 23 GCC
source patches without fuzz, native prerequisite fixes, and negative checker
fixtures for duplicate or foreign runtimes. The separate
[Zero 3W validation](native-validation.md) confirms the installed dependency
set and actual common pkgsrc selection. Self-hosting, current-binutils validation,
common consumer repairs and release-image integration remain unaccepted.

The [libxslt RVT ownership candidate](libxslt-security.md) carries the proposed
security repair with a tested release-wrapper correction. The common profile
requires current libxml2 for paired ID cleanup. Fresh-document registration
failures release their document and report the operation error. Functional, allocation-error and upstream tests
pass; normal package and dynamic memory acceptance remain separate.
