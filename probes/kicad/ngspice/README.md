# ngspice 47 for KiCad

This source probe prepares the current stable ngspice release for KiCad's
installed shared C API and the ngspice command line. It retains XSPICE,
CIDER, OSDI, KLU, OpenMP, FFTW and GNU Readline. The CLI uses batch mode
without the optional X11 plotting interface; KiCad owns its schematic UI.

Download the archive in `sources.tsv`. Run:

```sh
./prepare-source.sh /absolute/path/ngspice-47.tar.gz /absolute/new/source
```

The helper verifies SHA256, keeps the complete source and upstream licenses,
and applies `patches/series` without fuzz. Run `autoconf` and `autoheader`
before configuration because the patches modify `configure.ac`.
Use separate build directories for `--with-ngshared=yes` and
`--with-ngshared=no --with-readline=yes --with-editline=no --without-x`.
Both builds require `--enable-cider --enable-openmp --with-fftw3=yes
--enable-shared --disable-static`. XSPICE, KLU and OSDI remain enabled.

`build.sh native-bootstrap SOURCE NEW_WORK` builds both interfaces against
the selected host providers. Set `CC`, `CXX`, `PREFIX`, `CPPFLAGS` and
`LDFLAGS`. It stages the result beneath `NEW_WORK/stage`; it does not install
into the shared prefix. `build.sh target SOURCE NEW_WORK` additionally
requires `EMBERBSD_SYSROOT`, `EMBERBSD_GCC_RUNTIME`, `CC_FOR_BUILD` and
`TARGET_LIBTOOL`. It rejects target compilers other than GCC 16.2.0 with the
`aarch64--netbsd` triplet. Run installed contracts separately from building.
The helper installs the shared interface first and the CLI last. Both
interfaces use the resulting CLI-built XSPICE model modules. Their native
ELF payloads match the shared-build modules after excluding debug data and
build IDs. The installed shared-API check exercises this common module set.

A target build must use the common GCC16 compiler, the verified EmberBSD
sysroot, the matching GCC16 runtime and a native XSPICE generator. Never
execute the cross-built generator. Use the common target Libtool profile
for its NetBSD SONAME and runtime-path policy. Target installation uses
`/usr/pkg`; stage it with `DESTDIR` before package integration.

For registered target packages, use the ordinary
[pkgsrc CLI/shared recipes](../../../profiles/common-graphics/cross/ngspice.md).
Their compiler wrappers preserve the common runtime paths through Libtool.
The direct helper remains a source probe; calling the cross-host Libtool
outside its normal wrapper context is not a validated package build.

The target flags select both GCC16 CRT files and the matching `libgomp.spec`
through separate `-B` paths. A library `-L` path alone does not select OpenMP
development metadata. See the [real compiler regression](../../../profiles/common-build-tools/cross/openmp-spec.md).
Set `CC_FOR_BUILD` to the complete native compiler command. On Linux and
Darwin, keep its `-B/usr/bin/` argument when target wrappers precede host
binutils in `PATH`. Upstream configuration preserves that command for
the native XSPICE generator. Set `CFLAGS_FOR_BUILD` and `LDFLAGS_FOR_BUILD`
separately from target flags.

The patches repair bounded history substitution, circuit file replacement,
XSPICE cross generation, NetBSD loader/header selection, parsed token
ownership, pre-initialization, retained source-name lifetime, recoverable
parser-error ownership, command cleanup before controlled exit, malformed
vector expressions, the optional process-name return value and target memory
query selection during cross configuration.

The source-name pool lasts until session reset or quit. A rejected circuit
remains owned and current until explicit removal. `ngSpice_Circ` retains
its upstream return convention; consumers must inspect the error callback.
The command cleanup frame covers dispatch after substitution/redirection.
It does not claim to repair every earlier parser or command error path.

## Validation boundary

On 2026-10-18 the official stable-release page identified version 47. The
pinned archive and the initial 12 patches replayed without fuzz into a fresh source
tree. An independent source review found no blocking ownership issue.
The replay matches the edited source; only its provenance marker is additional.
The native bootstrap helper built and staged both interfaces with GCC 14.2.0
from the host image, FFTW 3.3.11 and Readline 8.3. Every selected feature
macro was present. The following checks ran on this new build:

| Check | Observed result |
|---|---|
| Installed shared C API | 18 checks passed: divider, resistor change, six-point sweep, XSPICE gain, circuit switch, parser rejection, reload, reset, reinitialization and compound quit |
| Installed CLI | Version 47, 96 repeated `-c` options under 32 descriptors, 4 V / -2 mA divider and malformed-vector rejection passed |
| Native XSPICE generator | Complete model paths, successful exit status and missing-input failure passed |
| History causal regression | Original source overflows its 512-byte array under UBSan; repaired 32 KiB substitution and negative cases pass UBSan and strict Memcheck without suppressions |
| Optional process-name file | Original source fails `-Werror=return-type`; repaired function returns NULL and passes strict Memcheck |
| Installed internal dot-card parser | Full 32 KiB current-vector name and missing-parenthesis rejection passed |

The raw shared-API Memcheck run found no invalid access or definite,
indirect or possible loss. Its strict all-leak gate returned 99 for 11,690
reachable bytes in 31 blocks: seven OpenMP/loader lifetime contexts. The
internal dot-card check retained 11,466 bytes in six such contexts. The CLI
also had no invalid access or lost blocks, but retained 312,129 bytes in
4,342 blocks across 433 contexts. These raw runs have no suppressions and
are not reported as clean all-leak passes. CLI process teardown is a separate
limitation from the shared-API ownership repairs.
An independent review approved seven exact reachable-only exceptions for
the native shared-API contract. The subsequent strict Memcheck run returned
0, with 11,690 bytes in 31 blocks suppressed and no other findings.
The exceptions cover OpenMP process state and seven retained XSPICE module
handles. They do not apply to failed loads, CLI teardown or target GCC16.

The actual KiCad 10.0.7 exported divider also passed with installed native
ngspice 47: 5 V input, 2.5 V output and -2.5 mA source current.
Its output checker rejected a mutated 3 V result.

GCC `-fanalyzer` and Clang Static Analyzer completed all 22 touched native
configurations on original and patched sources, using actual build arguments.
They retain inherited findings; successful analyzer exit is not a zero-warning
claim. Cppcheck 2.22.0 completed the same 22 configurations before and after
the patches. Its reports contain 555 and 554 entries, including informational
and inherited findings. The missing-return diagnostic is removed. Both
strict analyzer runs return 1; these are not clean analysis passes.
The full Cppcheck comparison attempted 1,680 configurations per source tree:
all CLI C units plus the touched shared-library units.
Both reports contain 19,252 entries. Errors decrease from 34 to 33;
warnings remain 998, portability findings 63, and informational entries 1,570.
Style findings change from 16,587 to 16,588. Analysis of the three OS-query units with the measured
Unix compiler macros produces identical findings: 42 information and seven style records, with no errors.
The other 30 inherited error records remain unclassified; they are not
30 confirmed source defects. The confirmed missing-return error is removed.
The ordinary GCC16 target packages `47nb1` pass installed API18, CLI, the exported
KiCad divider, BSIM OpenMP activation and package lifecycle checks in EmberBSD.
See the [package acceptance scope](../../../profiles/common-graphics/cross/ngspice.md)
for exact archive hashes. The target-memory patch limits the procfs
probe to Linux/Cygwin targets. All 13 patches replay without fuzz and match
4,378 files prepared by ordinary pkgsrc patch rules. A separate GCC16 native
and AArch64 [memory-query regression](tests/memory-query.md) validates that repair.
The installed library returns the independent positive NetBSD memory total without procfs
diagnostics. Target Memcheck and complete KiCad application acceptance remain pending.
Historical results from a lost workspace are not current acceptance evidence.

The reusable checks are in `tests/`. `api-contract.c` uses the installed
public header and library. `dotcards-contract.c` deliberately tests an
internal exported function and needs the matching source `wordlist.h`.
The history and process-name scripts compile actual pinned source bodies;
they are isolated regressions, not replacements for installed API tests.

See [PROVENANCE.md](PROVENANCE.md) for license and source ownership.
