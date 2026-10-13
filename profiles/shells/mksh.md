# mksh R59c control and port

The current release is R59c. The check on 2026-10-14 used the
[author's distribution mirror](https://mbsd.evolvis.org/MirOS/dist/mir/mksh/)
and the [author's Git mirror](https://github.com/mirabilos/mksh-cvs2git/tags).
The R59c tag points to `8b6f1b53521283f667b0b7644899feaddaf08d71`.
The primary mirbsd.org website returned HTTP 503 during the check.
No newer release appears in either available source.

The original `mksh-R59c.tgz` SHA256 is
`77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506`.
Its SHA512 also matches the local recipe's existing distinfo.
The Miros license and upstream attribution remain intact.

## Recipe and dependencies

The [ordinary recipe](../../pkgsrc/local-shells/mksh/Makefile) uses GCC 16.2.
The shell export replaces pinned pkgsrc's R59b source-copy recipe with R59c.
The archive suffix is `.tgz`. The recipe no longer requests the separate
pkgsrc printf implementation, which is absent from the upstream archive.
External `printf` remains available through the base utilities.

The runtime requires the system C library. Its editor is built into mksh;
libedit and ncurses are not additional dependencies. Tests use current Perl
5.44.0 and GNU ed 1.22.6. Both releases are current in pinned pkgsrc.
The export retains Ports' shared Perl recipe with its target portability repairs.
The control ed was also built with GCC16 and passed its own upstream suite.

## Source repairs

The local allocator repair keeps the previous allocation in its Area until
resizing succeeds. A size overflow or allocation failure can unwind to an
interactive shell. Its original object must remain owned and available for
cleanup. Successful relocation uses saved links without reading freed storage.

The arithmetic repair copies the evaluated result only after successful
evaluation. A recoverable syntax error previously copied an uninitialized
union field. The patches identify their AI-assisted origin and have not
been submitted upstream.

## Reproduce

Provide GCC 16.2.0, Perl 5.44.0, GNU ed 1.22.6 and Valgrind 3.27.1 on PATH.
The host-provider check also needs Cppcheck 2.22.0 and Clang 23.1.3.
Use a Linux host with `script` that propagates the child exit status.

```sh
export CC=/absolute/gcc16/bin/gcc CLANG=/absolute/clang
sh profiles/shells/host-tools/tail-control.sh /absolute/new-tail
export PATH=/absolute/new-tail/patched/prefix/bin:$PATH
sh profiles/shells/mksh-control.sh /absolute/new-mksh
sh profiles/shells/analyze.sh /absolute/new-mksh mksh
```

Use the script's final `upstream` argument in a separate fresh directory for the
comparison without our source patches. Both configurations retain the
upstream editor, job control and normal arithmetic support.
Cppcheck 2.22.0, GCC 16.2.0 and Clang 23.1.3 read recorded compiler arguments.
The analyzer script returns failure when Cppcheck reports findings.

## Measured scope

The patched GCC16 build passes all 568 upstream tests in a controlling PTY,
with no ignored cases. `FCEDIT` selects current GNU ed; the upstream
`stdout-ed,no-stderr-ed` categories match its observed byte-count output.
The earlier missing-editor skips are not retained as successful coverage.
The installed shell passes 16 POSIX checks and six command-substitution checks.
Staging matches all three PLIST paths. Source-payload installation, removal
and reinstallation retain identical program hashes without residual files.

Fourteen allocator cases exercise list-head, middle and tail nodes,
forced relocation, allocation failures and two overflow conditions.
The original allocator loses six blocks; the repaired allocator releases
every allocation. The arithmetic regression links real shell objects and
checks three recoverable errors plus successful arithmetic. The original
produces undefined data; the repair preserves the caller's initialized result.
Both negative controls fail Memcheck with status 97. The patched cases pass.

The memory contracts trace child programs and require every process summary
to be present and clean. The host's older GNU tail 9.7 leaks its file array;
the same normal-exit allocation remains in current coreutils 9.12. The
[host-provider patch](host-tools/patch-tail-exit.c) releases that array before
the final exit. File names retain their borrowed ownership. Its control
checks stdin, file, multiple-file, zero-line and missing-file behavior with
the original and patched current release. Earlier fatal exits and follow
mode are outside this repair. This is a test-host provider, not acceptance
of a coreutils package on EmberBSD. Original diagnostics remain available.
The final clean-commit mksh run uses this repaired provider. Every traced
process passes Memcheck, including both new source regressions.

## Analysis boundary

The upstream comparison covers all 16 C translation units. It reports 14
Cppcheck errors, 15 warnings, 14 portability messages, 1076 style messages
and 18 information messages; GCC reports three warnings and Clang 20.
All analyzer processes finish. These totals include inherited findings;
successful process status does not mean clean diagnostics.

After both repairs, Clang reports 19 warnings: the uninitialized arithmetic
read is removed. GCC and Cppcheck counts remain unchanged. Cppcheck still
reports the overwritten local allocator pointer; it does not follow the
ownership retained through the Area link. Source review and the allocation
failure regression check that path. Other warnings are not declared false
merely because executed tests pass.

The two new C regression programs are checked separately from these 16
production units. GCC and Clang report no finding. Cppcheck reports one
allocation-null warning because it does not propagate the failure guard
through the test's `require` helper; that guard terminates before use.
Its 22 style and two information messages are also retained.

Source review explains the three GCC reports: function lookup follows an
initialized global scope; the history queue keeps its saved non-null pointer;
`ksh_dup2` transfers the restored descriptor to its caller. Cppcheck's four
`tv1` reports omit the `TF_NOREAL` guard when no command is timed. A pipeline
status-name report misses the explicitly sized allocation for a trailing
array. No warning category is suppressed. Other reports in evaluation,
editing and variable handling require individual disposition.

The host-provider comparison covers `tail.c` with its actual GCC16 configuration.
Cppcheck 2.22 rejects two attributed gnulib function declarations. Its input
adapter preprocesses with the recorded GCC arguments, then removes redundant
parentheses around those two function names. Attributes and line markers remain.
The adapter prevents Cppcheck from expanding five floating-point enum names
a second time. GCC16 produces byte-identical assembly before and after this
normalization on both variants. Production sources remain unchanged.

After adaptation, Cppcheck reports no errors, two warnings, 269 style messages
and two information messages on each variant. The warnings concern the
single-stdin array model and an unchecked inherited `atexit` return value.
GCC reports no warning; Clang retains three null-pointer warnings on each
variant. The original parser failure and subsequent complete run are retained.
These results cover the host-provider translation unit, not all of coreutils.

## EmberBSD boundary

The control host is Linux x86-64. It establishes portable source behavior
and GCC16 compatibility for that configuration. It does not establish an
EmberBSD application sysroot, pkgsrc binary-package lifecycle, ARM64 login,
or target signal/job-control acceptance. No VM or device is used.
