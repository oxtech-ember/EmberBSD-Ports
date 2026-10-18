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

This checkpoint establishes source and focused native behavior.
The ordinary package with its default documentation, target cross package,
installed EmberBSD IPC tests and complete KiCad application remain pending.
