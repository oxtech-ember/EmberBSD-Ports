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
The installed provider passes the bounded EmberBSD IPC check below.
Native ordinary packaging and the complete KiCad application remain pending.

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

## Installed IPC transport check

[tests/ipc-smoke.c](tests/ipc-smoke.c) checks the installed NNG 1.12.3 provider.
KiCad 10.0.7 uses REP0 and filesystem `ipc://` sockets in
`libs/kinng/src/kinng.cpp` and `common/api/api_server.cpp`.
The check follows the public REQ0/REP0 flow shown by the pinned upstream
[request/reply example](https://github.com/nanomsg/nng/blob/v1.12.3/demo/reqrep/reqrep.c).
This independently written check uses BSD-2-Clause; see [LICENSE](LICENSE).
It does not copy the KiCad wrapper or serialize KiCad protobuf messages.

Use the common GCC16 compiler, a coherent EmberBSD sysroot and a new work
folder outside the sysroot. Run this example from `probes/kicad/nng`.
The example assumes the packaged GCC16 runtime:

```sh
target=x86_64--netbsd # Use aarch64--netbsd for AArch64 inputs.
cc=/absolute/toolchain/bin/$target-gcc
sysroot=/absolute/sysroot
work=/absolute/new-work
mkdir -m 700 "$work"
TMPDIR="$work" "$cc" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/$target/16.2.0/" \
    -std=c99 -O2 -g -Wall -Wextra -Werror \
    -I"$sysroot/usr/pkg/include" tests/ipc-smoke.c \
    -L"$sysroot/usr/pkg/lib" -L"$sysroot/usr/pkg/gcc16/lib" \
    -Wl,-rpath,/usr/pkg/lib:/usr/pkg/gcc16/lib \
    -Wl,-rpath-link,"$sysroot/usr/lib" \
    -Wl,-rpath-link,"$sysroot/lib" \
    -Wl,-rpath-link,"$sysroot/usr/pkg/gcc16/lib" \
    -lnng -o "$work/ipc-smoke"
```

Configure the [production target executor](../../../profiles/common-graphics/cross/introspection.md#compiled-configure-probes)
with this work folder as `build_root`. Run the resulting executable through
its `--execute` mode. The executor transfers and verifies the complete ELF
provider closure. It runs from a short private target directory and removes
that directory after execution. Direct execution also needs a short private
working directory. The check creates only its own `nng-ipc.XXXXXX` directory.
An abnormal hard-timeout exit relies on the enclosing executor for cleanup.

The check completes two exact binary request/reply exchanges. Each message
contains embedded NUL and non-ASCII bytes. It requires `NNG_ESTATE` when REP0
sends before a request, and `NNG_ETIMEDOUT` for an idle server and an unanswered
client request. Each successful allocated receive is freed once. Socket I/O
has explicit deadlines. A ten-second alarm covers execution and finalization.
It closes both sockets, finalizes NNG and removes its socket directory.

### Recorded AArch64 check

GCC16 AArch64 execution on EmberBSD passes all 25 checks with empty stderr.
A deliberate wrong-reply expectation fails with status 1 and the expected
message mismatch. Both production executions verify source/provider hashes
and complete remote cleanup. The executed library has SHA256
`37546affe7a66f39aaa2f6c49a88bd9b79afe6058dfad0d31fc4aac4fb3af042`.

GCC 16.2.0 `-fanalyzer`, Cppcheck 2.18.0 exhaustive analysis of the actual
GCC-preprocessed C99 source, and Clang Static Analyzer 21 with the same target
headers report no findings. Cppcheck emits only its active-checker report.
No checks or diagnostics are suppressed. That AArch64 target had no Valgrind.
Its selected toolchain and sysroot had no ASan or UBSan shared runtime.
GCC16 UBSan trap mode works without that runtime. The same consumer passes all
25 target checks with `-fsanitize=undefined
-fsanitize-undefined-trap-on-error -fno-sanitize-recover=all`.
The resulting ELF adds no sanitizer runtime dependency. A deliberate signed
overflow reaches the emitted AArch64 `brk` instruction and exits with status
133 (`128 + SIGTRAP`). Both executions complete remote cleanup.
This UBSan check covers only the consumer. The shared NNG library is not
instrumented. Valgrind and ASan were not run for this consumer; the separate
native NNG lifecycle Memcheck result above does not cover it.

### amd64 check

GCC 16.2.0 cross-builds the same public consumer against the normal NNG 1.12.3
package in a source-built EmberBSD SDK. Execution uses UID 0 with the existing
NetBSD 11.0 amd64 `GENERIC_TP` kernel and system ELF loader. The check covers
compatibility of the transferred user-space closure. EmberBSD kernel boot
acceptance remains separate.
The executor checks and stages SDK `libnng.so.1`, `libatomic.so.3`, `libc.so.12`
and `libpthread.so.1`. It reuses an installed file only when its SHA256 matches.
All four execution receipts agree with the transport status. Source/provider
hashes remain unchanged, the infrastructure marker is absent, and independent
checks confirm removal of each remote directory. No package is installed on
the execution target.

| Consumer case | Target result |
| --- | --- |
| Public REQ0/REP0 consumer | All 25 checks pass; status 0; empty stderr. |
| Private wrong-reply expectation | Status 1; `receive: message bytes or length differ`. |
| Public consumer with UBSan trap flags above | All 25 checks pass; status 0; empty stderr. |
| Deliberate signed-overflow control | Status 132, `128 + SIGILL`; no sanitizer runtime dependency. |

The executed amd64 NNG DSO has SHA256
`17976637f94b889163f6d38e273a87cc10bb91e1e7a345269c0e2ef5e3d7d10d`.
UBSan instruments only the consumer. The shared NNG library is not instrumented.
Valgrind is unavailable on the selected target system/package PATH. The selected
GCC16 runtime has no sanitizer shared library. Valgrind and ASan were not run
for this consumer. Root execution does not establish ordinary-user socket permissions.

This check accepts the installed transport provider and binary message flow.
It does not validate the KiCad request-server class, protobuf/API behavior,
package removal/reinstallation or a complete KiCad GUI session.
