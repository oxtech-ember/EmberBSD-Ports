# KiCad request-server lifecycle regression

This check compiles the actual KiCad 10.0.7 `KINNG_REQUEST_SERVER` source and
its unchanged header. It compares pinned upstream with
[`kinng-lifecycle.patch`](../../patches/kinng-lifecycle.patch).
The normal recipe's p0 patch and the source checkpoint's p1 patch must produce
exactly the source bytes used by the accepted target check.
KiCad source retains GPL-3.0-or-later and its original authorship notices.
The new harness and Python entry point use [BSD-2-Clause](../../LICENSE).
They were prepared with AI assistance.

The unit-only `wx/log.h` adapter removes trace logging from this check.
It does not implement wxWidgets. The normal KiCad recipe uses real wxWidgets
and receives no adapter include path. This is a selected class regression;
it does not accept wx logging, callbacks, protobuf/API or a full GUI workflow.

## Build and run

Use build-host CPython 3.15 and an explicit SDK source with API 1, producer
stream API 1 and inspection API 1. No pip packages are required.
The compiler and the coherent target sysroot must provide common GCC16 and
NNG 1.12.3. All compilation runs on the development host.
Pass absolute paths and a new work directory outside the inputs:

```sh
python3.15 -E -S probes/kicad/application/tests/kinng/lifecycle.py \
    --sdk-source /absolute/EmberBSD-SDK \
    /absolute/kicad-10.0.7.tar.bz2 \
    /absolute/toolchain/bin/aarch64--netbsd-g++ \
    /absolute/sysroot /absolute/new-kinng-work
```

The script verifies the archive, source and header hashes. It extracts only
the selected class, header and license/author files. It applies both patch
forms with zero fuzz and compares their result with the executed candidate
SHA256. It cross-builds upstream and candidate with GCC16 UBSan trap mode.
It verifies ELF architecture and the absence of a UBSan runtime dependency.
The CLI also accepts the common `x86_64--netbsd` toolchain. This checkpoint
qualifies builds and execution only on AArch64.

To execute all eight causal cases, add `--query-config /absolute/query.json`
to the same command and select a different new work path. The query JSON must
contain this work in its `build_root`. It must select the same target sysroot.
Use the [production target transport](../../../../../profiles/common-graphics/cross/introspection.md#compiled-configure-probes)
with a verified SSH host. The CLI calls the production query implementation
in-process and reuses its SDK producer control, provider checks and cleanup.
Run target checks only while you own the query service's execution window.
Without `--query-config`, the receipt explicitly marks execution as unrequested.

The script leaves failed or incomplete work for inspection. A process ownership
failure also leaves `producer-ownership-unconfirmed`; retain that work and do
not reuse it. The receipt contains commands, hashes, ELF providers, source
identities and executed results. Keep the target query receipts with it.

## Causal cases

| Mode | Upstream status | Candidate status | Independent witness |
| --- | --- | --- | --- |
| `ownership` | 1 | 0 | Sixteen real allocated server receives leave sixteen buffers before the patch and zero after it. |
| `stop` | 124 | 0 | A real receive precedes `Stop`. The upstream child reaches its deadline; the candidate returns without a reply. |
| `create-error` | 1 | 0 | A real unsupported listener URL leaves the upstream socket open. The candidate closes it. |
| `start-error` | 1 | 0 | Injected `NNG_EADDRINUSE` must close the socket without entering receive. The upstream class enters receive. |

ELF wrappers call the real NNG receive/free functions. They count successful
allocated buffers returned to the actual class. The baseline's retained
buffers are freed manually only after the ownership witness is recorded.
This targeted witness establishes ownership behavior; it is not Memcheck.
The start-error control injects one listener result. The ordinary exchanges
and invalid listener-create transport use real NNG behavior.

The exchange modes wait for a real successful listener start before dialing.
The bounded readiness wait does not replace the receive or stop markers.
The stop mode forks before NNG initialization. Its parent bounds its exact
owned child to three seconds and reaps it. The baseline must print
`STOP_ENTERED_AFTER_REAL_RECEIVE` and `STOP_SUBPROCESS_DEADLINE` and return 124.
The candidate must print `STOP_RETURNED_WITHOUT_REPLY` and return zero.
A twelve-second alarm bounds the whole harness. Socket operations also have
deadlines. The harness removes its owned socket directory; the production
transport separately verifies hashes and removes its private remote directory.

## Acceptance and limits

All eight baseline/candidate AArch64 cases pass through the production target
CLI. The public Python entry point also rebuilds from the pinned archive,
verifies both patch forms and passes the same eight-case matrix through the
production implementation. Candidate stderr is empty and all remote cleanup
statuses are zero.
The actual class and harness are compiled with GCC16 UBSan trap mode; the NNG
and libstdc++ shared dependencies are not instrumented. No Valgrind or ASan
result is claimed for this class regression.

Clang Static Analyzer 21 uses the target headers and GCC16 C++ include paths.
It reports no findings for baseline, candidate or the harness with the explicit
logging adapter. Cppcheck 2.22 stops in the actual GCC-preprocessed units at
`sys/endian.h`'s extern-C closing declaration. It establishes no completed
Cppcheck coverage. No diagnostic category or check is suppressed.
Normal full KiCad package, real wxWidgets integration and GUI acceptance remain
pending. The separate [NNG backend check](../../../nng/README.md#installed-ipc-transport-check)
accepts its transport provider and does not replace this class regression.
