# NNG 1.12.3 lifecycle source checkpoint

KiCad IPC uses the maintained stable NNG library.
The [pinned source](PROVENANCE.md) retains the public ABI, protocol and
compatibility headers, runtime features and upstream build defaults.

The private lifecycle patch drains asynchronous operations, tasks and reaped
objects before it destroys their shared state. A reinitialized library also
restarts its cleanup worker. The patch adapts three upstream fixes by
Garrett D'Amore and retains their cancellation regressions.

Native GCC16 builds both the shared public library and the full upstream test
library. Both upstream sleep/finalization controls exceed an eight-second
deadline with the unpatched stable library. The patched controls complete,
including 2000 pending sleeps and sequential library lifecycles.
The unchanged socket-accept test reproduces invalid-mutex teardown with
the stable library; the repaired native test completes.

The full native suite passes 99 of 100 tests. The external HTTP client test
still times out against public servers. The local HTTP server test passes.
The suite retains its HTTP test and runtime features.

Strict native Valgrind 3.24 checks pass the socket-accept control and the
combined sleep/finalization controls with zero errors and zero live allocations.
GCC16 `-fanalyzer` and Clang 19 analysis report no findings for nine actual
library/test translation units before and after the source patch.
Cppcheck 2.22 stops at the real Linux `types.h` signed-128-bit declaration.
Its experimental Clang import also fails on a real AST location.
These parser failures do not establish completed Cppcheck coverage.

The ordinary [common NNG package](../../../profiles/common-graphics/cross/nng.md)
now uses this exact reviewed source patch. Its GCC16 AArch64 package retains
all 325 manual pages and 325 HTML pages with the default documentation option.
Native ordinary packaging, installed EmberBSD IPC tests and the complete
KiCad application remain pending.

The ordinary AArch64 build also supplies the real preprocessing flags and
EmberBSD headers for four patched runtime units: `aio.c`, `init.c`, `reap.c`
and `taskq.c`. GCC 16.2.0 `-fanalyzer` reports no diagnostics before or after
the lifecycle patch. Cppcheck 2.18.0 parses the GCC-preprocessed C units with
`--language=c --std=c99 --platform=unix64 --check-level=exhaustive`.
It reports no errors, warnings or parser failures before or after the patch.
It reports 62 style diagnostics before and 63 after, plus four checker reports
in each set. The difference removes one `variableScope` diagnostic and adds
one `staticFunction` and one `redundantContinue` diagnostic. These are style
findings in the private upstream lifecycle implementation. They are not
confirmed runtime defects. No diagnostics are suppressed.
This check covers the selected NetBSD/AArch64 feature configuration and four
runtime units. It does not establish whole-library or Windows coverage.
The earlier Linux Cppcheck parser limitation remains a separate boundary.
