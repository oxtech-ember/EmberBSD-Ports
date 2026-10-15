# Pinned upstream ncnn controls

These controls compile eight unchanged test translation units from ncnn
20260526. They link to the installed shared library through its exact-version
CMake package. The selected tests cover the C API, parameter and expression
parsers, ReLU, pooling, dense layers, softmax and convolution. Upstream's
`testutil.cpp` compares optimized operators with reference implementations.
Each test has a 600-second deadline. These tests do not cover every operator.

```sh
cmake -S probes/ncnn/tests/upstream -B /absolute/upstream-tests \
  -DCMAKE_PREFIX_PATH=/absolute/sdk \
  -DNCNN_SOURCE_DIR=/absolute/verified-patched-source
cmake --build /absolute/upstream-tests --parallel 2
ctest --test-dir /absolute/upstream-tests --output-on-failure
```

Use the documented toolchain file for cross compilation. Run the resulting
programs on EmberBSD. Cross compilation alone does not execute these tests.

The optional CPU controls compile the actual baseline and patched `cpu.cpp`
directly. Set `NCNN_BASELINE_SOURCE_DIR` to the unmodified pinned source and
`NCNN_CONFIG_DIR` to the runtime build directory. No substitute syscall or
copied CPU implementation is used. On an EmberBSD guest with two online CPUs,
`ncnn-cpu-source-before` must return 2 and report one logical CPU. The patched
`ncnn-cpu-source-after` must return 0 and match `sysconf(_SC_NPROCESSORS_ONLN)`.
The baseline is a negative control, so it is not registered as a passing CTest.
The patched control also checks the declared baseline NEON feature policy and
the explicit failure of unsupported NetBSD affinity.

The two `ncnn-cpu-first-use-*` programs release eight caller threads together.
They exercise the actual CPU initialization code through 264 CPU queries.
Run these programs under Valgrind DRD on Linux with GCC16. The baseline
must report conflicting accesses to the CPU initialization flag and cached
metadata. The patched program must report zero unsuppressed DRD errors. Ordinary
numeric output alone does not expose this race. The POSIX patch replaces
the unsynchronized first-use flag with `pthread_once` when threads are enabled.
It preserves the ABI and the existing single-thread and Windows paths.

```sh
valgrind --tool=drd --error-exitcode=99 \
  /absolute/upstream-tests/ncnn-cpu-first-use-after
```

Valgrind 3.24 Helgrind on the Linux glibc 2.41 build host does not model
`pthread_once` completion publication fully. It retains one read/write context
after this fix, including in a minimal control using the real primitive.
The unannotated DRD run provides the race regression. The tool's shipped
default suppressions remain active. No custom suppression, synchronization
annotation or replacement primitive is used. The recorded Helgrind result
retains seven unsuppressed reports in one context after the fix.

NetBSD affinity, heterogeneous core classification and optional ARM ISA
detection remain unsupported. The physical-core API retains upstream's
logical-count fallback on this platform. OpenMP is disabled in the accepted
profile. `NCNN_THREADS=ON` supplies pthread-backed synchronization and consumer
threads; it does not parallelize operator loops when OpenMP is disabled.
