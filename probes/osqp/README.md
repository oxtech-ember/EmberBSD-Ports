# OSQP 1.0.0 on EmberBSD

The [ordinary package](../../pkgsrc/local-robotics/osqp) cross-builds with
GCC 16.2.0 and passes installation and numerical checks in EmberBSD AArch64
QEMU on 2026-10-14. OSQP supplies a shared C quadratic-programming solver with
the current QDLDL 0.1.9 direct backend. Ports owns its recipe and consumer tests.

The selected configuration uses double precision, 64-bit indices, adjoint
derivatives, timing, printing and the POSIX interrupt listener. QDLDL is an
object dependency inside libosqp. The package contains 19 files: public OSQP
and QDLDL headers, CMake exports, the shared library and license/provenance files.
Code generation, language bindings and external algebra backends are outside
this selection. Upstream test archives and Catch2 do not enter the package.

## Cross build and target checks

```sh
./cross-build.sh /absolute/gcc16-prefix /absolute/emberbsd-sysroot \
    /absolute/cache/osqp-1.0.0.tar.gz /absolute/cache/qdldl-0.1.9.tar.gz \
    /absolute/new-osqp-output
```

Use a sysroot built from the fork, including its GCC16 CRT/runtime. Keep the
upstream `aarch64--netbsd` triplet and `NetBSD` CMake platform. Accepted OS source
revision: `267ee85eee1027198175809a8b7b0572df36ad1e`.
[sources.tsv](sources.tsv) records both archive SHA256 values. The helper checks
all native recipe patch hashes, applies them with zero fuzz and configures
disconnected FetchContent. It uses the same [feature cache](../../pkgsrc/local-robotics/osqp/features.cmake)
as the package. It installs every upstream interface and verifies PLIST equality.

The three consumer programs resolve the exact staged CMake package. Their ELF
reports verify AArch64 and exclude host paths from runtime linkage. Package the
stage with [package-cross-stage.sh](../../scripts/package-cross-stage.sh), using
the actual external library requirements and build options. Run:

```sh
./run-target.sh /absolute/osqp-1.0.0.tgz \
    /absolute/osqp-contract /absolute/osqp-interrupt \
    /absolute/osqp-derivative /absolute/new-results
```

The target driver requires real EmberBSD/NetBSD AArch64. It uses pkg_add,
pkg_info, pkg_admin, ldd and pkg_delete without loader-path overrides. It proves
removal of registration/library files, failure of the removed consumer and
successful numerical execution after reinstallation.

| Installed check | Accepted result |
| --- | --- |
| Analytic QPs | Independent optima, KKT stationarity, complementarity, objective and finite bounds |
| Updates | Linear cost, Hessian and bound updates plus warm start match separate analytic solutions |
| Infeasible problem | Status and independently verified primal infeasibility certificate |
| Derivatives | Scalar inactive-bound QP gives x=0.5, dL/dq=-0.5, dL/dP=-0.25 and zero bound derivatives |
| Interrupts | Actual SIGINT is detected; the prior handler is restored |
| Package cycle | Integrity, removal and reinstallation pass |

## Upstream tests and source repairs

A separate test build enables upstream's required static archive and test
programs. It uses the same numerical backend/features as production. Current
Catch2 3.16.1 replaces the original 2.13.6 harness with a test-only compatibility
patch. Assertions remain unchanged; one malformed tag gains its missing bracket.

Upstream's test-data generator requires Python. The accepted host uses Python
3.13.5, NumPy 2.5.4 and SciPy 1.18.1. Its current wheels match official PyPI
hashes. No project-owned Python utility or target Python dependency is added.
QDLDL and Catch2 use verified local sources with disconnected FetchContent.

All three native and AArch64 upstream programs pass with seed 42:

| Program | Cases | Assertions |
| --- | ---: | ---: |
| lin_alg_tester | 28 | 177 |
| osqp_tester | 30 | 424 |
| osqp_tester_custom_memory | 30 | 424 |

The NetBSD source-selection repair enables OSQP's existing POSIX listener.
The original source-list fixture fails and the patched fixture passes. It
preserves the fork's platform identity and uses the existing clock_gettime timer.

The QDLDL constructor repair checks two calloc results before dereference.
The separate [allocator-hook regression](tests/allocation-failure.c) injects
failure of the private solver object and its CSC object. Both original cases
crash with SIGSEGV. Both patched cases return OSQP_MEM_ALLOC_ERROR, release all
allocations and preserve a normal solve. The same control passes in AArch64.
The hook build is isolated and never replaces the production allocator.

## Analysis and limits

Cppcheck 2.17.1 covers all 29 production C translation units with the actual
target compilation database. Diagnostics are retained: 199 style, 12 warning
and one AMD negative-index finding. The latter depends on the initialized
nonnegative child-front invariant; no supported-input reproduction was found.
GCC16 -fanalyzer also covers production sources. After the two constructor
repairs, the QDLDL unit retains an ownership-leak diagnostic and a possible
allocation failure in rho_inv_vec. Other allocation failures remain outside
the bounded repair; this is not a complete out-of-memory safety claim.

On supported x86_64 Linux, all upstream programs, installed numerical/listener
controls and the forked allocation regression pass Valgrind 3.24.0. Their
records show zero errors, no suppressions and zero retained bytes. The new
derivative contract also passes Cppcheck and GCC -fanalyzer.

The VM uses QEMU 10.0.13 TCG, Cortex-A72, two CPUs and 2 GiB RAM. These are
software numerical checks. They do not establish real-time deadlines, actuator
safety, every possible matrix/input or sustained operation on a physical board.

The native NetBSD helper remains [build.sh](build.sh) followed by [test.sh](test.sh).
Its source profile uses the same current dependency and repairs. Earlier macOS
contracts remain a separate host record. See [PROVENANCE.md](PROVENANCE.md)
for original authors, licenses and adaptation ownership.
