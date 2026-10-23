# dash 0.5.13.5 control and port

Version checked on 2026-10-14 against the
[authoritative tag list](https://git.kernel.org/pub/scm/utils/dash/dash.git/refs/).
The latest release is `v0.5.13.5`, dated 2026-07-17, at
`037bbdfd330017c368caf6242f977974123239b5`.
The release archive SHA256 is
`40090101a2a491f13e901d3d48e90414f26634628b9bfff35ff540363c227a7d`.
The author's download server returned HTTP 503 during this check; the
pkgsrc mirror supplies bytes matching the pinned upstream release SHA512.

## Configuration and dependencies

The [ordinary recipe overlay](recipes/shells/dash/Makefile) keeps libedit
support enabled and selects GCC 16.2. The package export uses libedit
from the qualified EmberBSD base and its native terminfo provider.
An outdated base stops consumer builds. The portable control below uses
[libedit 20260512-3.1](https://thrysoee.dk/editline/) from the
[canonical recipe](../../pkgsrc/devel/editline).
The library preserves wide-character and readline interfaces and the four
existing pkgsrc portability patches. Its configure check also recognizes
ncurses' current wide-library name, `libncursesw`.

The control host is Linux x86-64 with GCC 16.2.0, Autoconf 2.73,
Automake 1.19, Libtool 2.6.2 and Perl 5.44.0. Production C compilation uses
`-O2 -g` with actual compiler arguments recorded per translation unit.
The installed dash loads the selected libedit and ncurses from the control
prefix, not the host's older libraries. The earlier no-libedit experiment
is not the acceptance configuration.

## Source repairs

- The parser no longer reads an uninitialized `saveprompt` into itself.
  Its existing conditional assignment and restore remain intact.
- Clearing inherited traps frees the saved string, not the pointer already
  set to `NULL`. EXIT processing releases its detached handler string on
  both normal return and `longjmp`. Independent source review checked the
  fork/vfork and jump-buffer lifetimes.
- `evalstring` accepts a const input string from current libedit history.
  Evaluation still copies it into owned stack storage. No const-removing
  cast or warning suppression is used.

The [patches](recipes/shells/dash/patches) are local, not accepted upstream.
They preserve licenses and identify their provenance.

The current libedit dependency also receives two ownership repairs:
completion generators release all accumulated strings when result-array
growth or common-prefix allocation fails. A consumer linked to the actual
static library injects five allocation failures across the native and
readline-compatible APIs. The original library leaks; the patched library
passes those cases and the successful case with all allocations released.

## Reproduce

Provide the tool versions above, Cppcheck 2.22.0, Clang 23.1.3, Valgrind
3.27.1 and Ruby with its standard PTY library. The dependency prefix must
contain a GCC16-built ncurses 6.6 with wide-character support.

```sh
export CC=/absolute/gcc16/bin/gcc
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
  sh profiles/shells/editline-control.sh /absolute/new-editline /absolute/ncurses /absolute/libedit.tar.gz
NCURSES_PREFIX=/absolute/ncurses \
  sh profiles/shells/dash-control.sh /absolute/new-dash /absolute/new-editline/prefix
sh profiles/shells/dash-traps.sh /absolute/new-dash/prefix/bin/dash /absolute/new-trap-check
ruby profiles/shells/dash-editline.rb /absolute/new-dash/prefix/bin/dash
CLANG=/absolute/clang sh profiles/shells/analyze.sh /absolute/new-dash dash
```

`dash-control.sh` accepts a final `upstream` argument for comparison before
our three source patches. Both variants retain the pinned pkgsrc platform
patches and the same enabled features. Use separate fresh output directories.
The comparison is between matching configured sources; no old release is
retained as a dependency.

The analyzer command deliberately returns nonzero when it reports findings.
Read the raw XML and per-source logs; a successful compiler process does not
mean its diagnostics were clean.

## Measured scope

The GCC16 build and installation pass. `make check` succeeds but dash ships
no upstream tests through that target, so it is not counted as a test suite.
The installed program passes 16 POSIX behavior checks, six old/new command
substitution checks, and real-PTY editing, history recall and `fc -s`
substitution. Staged install, uninstall and reinstall produce identical
file hashes without residual files.

Nine trap lifecycle cases pass Valgrind with no invalid accesses,
uninitialized-value errors or definite/indirect/possible leaks. The same
normal EXIT case fails against the comparison build with Memcheck status
97. Checks include an EXIT action that calls `exit`, an action that fails,
inherited trap reset, trap listing, replacement and an external command.
Process-lifetime reachable allocations are reported, not suppressed.

libedit passes 32 installed input, history, narrow/wide tokenizer and
cleanup lifecycles, plus staged install, uninstall and reinstall. Its
`make check` target also has no upstream test suite. Full static analysis
covers 61 PIC/non-PIC compilation commands (32 C files, including examples).
The platform-only patches introduce no new diagnostics; the completion
repair removes Clang's confirmed allocation-leak finding. Remaining
inherited reports include two Cppcheck errors and six warnings and require
the same explicit triage discipline as dash. The allocation regression
does not establish that every library failure path is correct.

## Static analysis

Cppcheck, GCC `-fanalyzer` and Clang Static Analyzer cover all 32 recorded
dash compilation commands, including generated code and libedit support.
Cppcheck also reads compiler-provided include paths and definitions.
Production sources are unchanged for analysis. Two documented parser
normalizations apply only to Cppcheck input: GNU `__signed__` is spelled
`signed`, and `-!block` is parenthesized as `-(!block)`. A minimal fixture
reproduces the Cppcheck 2.22 parsing error; GCC16 emits identical assembly
for the original and parenthesized job-control source after ignoring the
assembly source-name directive.

| Diagnostics | Before local repairs | After local repairs |
| --- | ---: | ---: |
| Cppcheck errors | 2 | 1 |
| Cppcheck portability messages | 18 | 18 |
| GCC warnings | 9 | 7 |
| Clang analyzer warnings | 24 | 23 |

All diagnostic categories remain enabled. Style/information messages are
also retained in the XML. The remaining Cppcheck error concerns `savehandler`
across `setjmp` in history execution: the handler is initialized before the
local jump buffer becomes active. Clang's pipeline warning assumes a
one-command `NPIPE`, whereas the parser constructs at least two commands.
These are reviewed modeling limitations. Remaining inherited path warnings
in alias, builtin test, expansion, parser, redirection and variable handling
still need individual disposition; this is not a clean static-analysis
claim. No newly introduced memory failure appeared in the executed controls.

## EmberBSD boundary

The recipes retain BSD feature checks and use the current common compiler
and dependency selection. This run does not provide an EmberBSD application
sysroot or a GCC16 target package execution result. The portable source fixes
and Linux controls do not prove ARM64 login, `chsh`, signal/job-control
behavior under an EmberBSD kernel, or pkgsrc binary-package lifecycle.
Those acceptance steps remain separate; no VM or device was used here.
