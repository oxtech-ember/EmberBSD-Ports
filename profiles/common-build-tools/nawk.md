# Shared bundled nawk

Origin: EmberBSD adaptations are AI-assisted. Original licenses remain intact.

The shared `lang/nawk` recipe selects One True Awk snapshot 20260426,
commit `5739fd79bcfc75ba7526773d0cf634521f8aca3c`.
The project [does not normally make formal releases](https://github.com/onetrueawk/awk/blob/20260426/README.md).
On 2026-10-24, the latest tag and upstream master name that exact commit.
The [official comparison](https://github.com/onetrueawk/awk/compare/20260426...master)
contains no later commits. No untagged fix or second snapshot is required.
`pkgsrc/lang/nawk/SOURCE.json` pins the archive URL, SHA256, size and file map.
The common source manifest pins the same bytes.

The replacement recipe supplies one bundled source tree to both the initial
bootstrap copy and the ordinary package extraction. The upstream pinned
pkgsrc recipe remains the immutable donor; `pkgsrc/replaces` selects the new
owner for every source composition. The common tools replacement floor
rejects installed nawk 20250726 and retains stronger caller requirements.
The bootstrap self guard prevents a circular awk dependency.
The fixed initial `darwin-installed-utilities-v1.json` profile describes its
original installed seed bytes. It is not ordinary provider admission and is
not rewritten as a receipt for this source update.

## Source adaptations

This snapshot adds upstream UTF-8 and CSV behavior. String operations count
Unicode code points. Review byte-count assumptions in consumers and run
upstream UTF-8/CSV tests during native acceptance.

The bundled `lib.c` preserves the [NetBSD ctype repair](https://github.com/NetBSD/pkgsrc/commit/7099c72bfddcbf9671d3a3478636cf05e73bbfaa).
Byte arguments use unsigned-char casts before classification or conversion.
The adaptation also covers new hexadecimal and format-width checks.
Wide-character operations keep their upstream behavior.

The local `split()` memory fix uses the existing checked `tostring()` helper
for source and separator copies. The CSV scratch allocation includes the NUL
byte and reports allocation failure through `FATAL`. The source gate binds
these exact changes to the pinned upstream bytes. Source checks do not
establish allocator-failure, sanitizer or package runtime acceptance.
Upstream source, licenses, FIXES, FIXES.1e and all test cases remain in the bundle.
The testdir harness requires explicit `CC`, `awk` and `oldawk` selections.
It honors `CPPFLAGS`, `CFLAGS` and `LDFLAGS` for its native echo helper.
No system compiler or reference awk is selected by default.
The manual uses the installed `nawk` command and retains the original book title.
The derived build Makefile retains the complete upstream Lucent copyright
and permission notice. The source gate compares that block byte for byte.

The build Makefile consumes pre-generated parser files and `proctab.c`.
It uses the selected compiler and linker flags in bootstrap and ordinary
builds. It does not build or run a host parser generator.

For a prepared native test tree, select an executable in `CC` and pass
flags separately. `CC` must not contain arguments or a command tuple.
Select the comparison interpreter explicitly through the SDK scope too.

```sh
cd /absolute/private/nawk-test-tree
CC=/absolute/selected/gcc16 \
CPPFLAGS='SELECTED_CPPFLAGS' CFLAGS='SELECTED_CFLAGS' \
LDFLAGS='SELECTED_LDFLAGS' \
awk=/absolute/private/nawk-test-tree/a.out \
oldawk=/absolute/selected/comparison-nawk \
    /absolute/selected/sh ./REGRESS
```

## Explicit command shell

The optional `NAWK_COMMAND_SHELL` recipe variable selects the command shell.
It must name an absolute path with only ASCII letters, digits, `_+./-`.
The ordinary recipe passes that path as a C string macro with the same name.
A direct source producer must pass the macro as one compiler argument.
Without the macro, `system()` and `popen()` keep their libc behavior.

The opt-in adapter supports NetBSD and POSIX hosts, including Darwin and Linux.
Their default build is unchanged.
Cross builds select the shell path for the machine that will execute nawk.
This option does not select a compiler, admit a provider or qualify an SDK.

`files/command-shell.h` adapts the BSD `system()` signal and wait rules.
Its copyright notice retains the University of California license.
The source references NetBSD `system.c` revision 1.28 and OpenBSD revision 1.13.
The child executes the selected shell directly and exits 127 if execution fails.
The parent retries an interrupted wait and restores signal dispositions and masks.
NetBSD `popenve()` keeps libc's pipe registry and the existing `pclose()` contract.
Other POSIX hosts use the BSD pipe, fork, descriptor, and wait rules.
Their private pipe registry belongs to the single-threaded nawk interpreter.
Both close call sites use `nawk_pclose()` to reap the matching child.
Each pipe child closes descriptors inherited from earlier nawk pipes.
Allocation, pipe, stream, fork, and wait failures release the owned resources.
The pipe adaptation retains NetBSD `popen.c` revision 1.38 and Ken Arnold's provenance.
No host libc is replaced.

The Darwin bootstrap profile selects `${LOCALBASE}/bin/mksh` for the installed nawk.
The recipe retains a runtime dependency on that shell package.
An initial source build can instead pass its explicit initial mksh path.

The source check validates actual recipe flag transport and rejects invalid paths:

```sh
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-command-shell.py \
    --recipe /absolute/Ports/pkgsrc/lang/nawk \
    --bmake /absolute/selected/bmake --work /absolute/new-selector-check
```

The source-owned `bootstrap/command-shell-probe.c` includes the production header.
A native producer compiles it with the recipe's `files/` include path
and the exact selected-shell macro. The probe takes no arguments.
It prints `PASS: nawk command-shell contracts` only after all checks pass.
It checks exit and signal statuses, read/write pipes and `pclose()` status.
All successful shell commands in the probe use shell builtins.
The read-pipe case passes a plain literal to `echo` and checks its final newline.
The signal-status check uses SIGKILL because a shell can catch other signals
and exit normally during cleanup. A separate SIGINT trap checks that a caught
parent disposition does not become an ignored child disposition. The ignored
parent case must still leave SIGINT ignored in the child.
Injected syscall failures check `EINTR`, fork/exec errors and signal-state restoration.
Run the default build separately in a scope that admits the platform shell.
The initial explicit-shell producer must not use this default as a hidden fallback.

Run the probe and relevant upstream cases with the selected native GCC16.
Run Cppcheck, GCC path analysis and applicable memory analysis on the actual inputs.
Trace child execution to verify the shell route in real awk `system()` and pipes.
Source checks and a dry-run do not establish compilation or native execution.

`tests/nawk-command-shell.py --darwin-profile` evaluates the real Darwin profile,
the recipe compiler argument, repeated includes, and the shell dependency.
The same command can check the NetBSD profile with `--netbsd-profile`.
The native interpreter checks use this command:

```sh
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-shell-runtime.py \
    --awk /absolute/new/nawk --work /absolute/new-runtime-cases
```

It checks mksh identity in `system()` and both pipe directions.
It also checks command failures, signal status, pipe reopen, fields, arrays, and regex operations.

## Parser source preparation

The upstream makefile defaults to Bison. The BSD bundled integration selects
a pinned byacc to prepare `awkgram.tab.c` and `awkgram.tab.h`.
A selected native GCC16 builds upstream `maketab.c`; that helper produces
`proctab.c`. Do not reuse tables from the preceding source snapshot.

```sh
SELECTED_PYTHON -B pkgsrc/lang/nawk/regenerate.py \
    --source /absolute/Ports/pkgsrc/lang/nawk/files \
    --byacc /absolute/selected/byacc --cc /absolute/selected/gcc16 \
    --ccflags 'SELECTED_NATIVE_FLAGS' --work /absolute/new-generator-work
```

`--plan` prints argv without running generators or writing files.
Select and admit the interpreter, generator and GCC16 producer through the
SDK contract before an actual run. This helper does not qualify its tools.
It writes exact argv and diagnostics to private evidence.
Review and copy only the three generated source files and `GENERATED.json`
into `files/`. The public manifest records input/output hashes and tool
identities without private paths. Repeat generation must produce the same bytes.

## Source and metadata checks

```sh
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-source.py \
    /absolute/distfiles/nawk-20260426.tar.gz /absolute/Ports/pkgsrc/lang/nawk \
    /absolute/new-source-check --bmake /absolute/selected/bmake
SELECTED_PYTHON -B profiles/common-build-tools/tests/nawk-metadata.py \
    --tools-mk /absolute/prepared-pkgsrc/mk/tools/replace.mk \
    --bmake /absolute/selected/bmake --pkg-admin /absolute/selected/pkg_admin \
    --work /absolute/new-metadata-check
```

`--source-only` verifies the pinned source, licenses, tests and BSD casts.
It does not accept missing generated data. The default gate also verifies
parser inputs, output hashes, token-table agreement and the actual make plan.
Negative controls reject changed archive bytes, lost casts, changed licenses,
changed pins and foreign source paths. Metadata controls reject the old tool
provider and preserve a stronger caller, the self guard and unselected tools.
These checks do not establish C compilation, analysis or target/native runtime.
