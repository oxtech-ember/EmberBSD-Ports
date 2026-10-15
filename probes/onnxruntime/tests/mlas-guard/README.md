# MLAS guarded-buffer regression controls

These controls include the actual upstream `test_util.h` header. The baseline
uses pristine ONNX Runtime 1.31.0. The patched target uses the runtime source
tree with the canonical `patch-mlas-guard-pages` change.

NetBSD PaX prevents adding mapping permissions that the original `mmap` call
did not declare. The patch keeps the initial protection at `PROT_NONE` and
declares future read/write permission with `PROT_MPROTECT`. It then commits
only the data pages. The upper guard pages stay inaccessible. POSIX allocation
failure is `MAP_FAILED`, not a null pointer.

```sh
cmake -S probes/onnxruntime/tests/mlas-guard -B /absolute/guard-controls \
  -DORT_PRISTINE_SOURCE=/absolute/pristine-onnxruntime \
  -DORT_SOURCE_DIR=/absolute/patched-onnxruntime \
  -DORT_BUILD_DIR=/absolute/runtime-build \
  -DGTEST_SOURCE_DIR=/absolute/verified-googletest \
  -DCMAKE_PREFIX_PATH=/absolute/eigen-prefix \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build /absolute/guard-controls --parallel 1
ctest --test-dir /absolute/guard-controls --output-on-failure
```

Use the production CMake toolchain for a cross build. The helper imports
production ThreadPool definitions and uses the real target headers. It does
not fetch dependencies. Ruby checks the exact negative baseline result.

Both binaries accept one argument:

- `--real` uses real mapping, protection, and release calls. The patched binary
  must exit zero. On EmberBSD with PaX active, the baseline prints the rejected
  `mprotect` result and exits four with `FAIL real guard mapping aborted`.
  Linux can accept the baseline reservation and does not exercise NetBSD PaX.
- `--fail-map` injects `MAP_FAILED` with `ENOMEM`. The baseline reaches
  `mprotect`, prints `FAIL mapping failure reached mprotect`, and exits three.
  The patched header aborts before that call. The harness verifies the call
  counters, prints `PASS mapping failure stopped before mprotect`, and exits zero.
- `--guard` adds a child-process read immediately after the valid data. The
  patched parent must observe `SIGSEGV` and exit zero. The child cannot write a
  core file. This verifies the inaccessible guard instead of relaxing PaX.

Linker wrappers report syscall arguments and errors. They call the real
mapping APIs except for the named allocation-failure injection. The abort
wrapper converts the recorded fail-fast stage into an exact test result.
It does not return to the upstream code.

Run patched `--real` and `--fail-map` under strict native Memcheck. Do not run
the intentional child fault under Memcheck as a clean-memory scenario.
The header retains Microsoft Corporation's MIT notice. These controls test
the MLAS test allocator. The selected 76 upstream tests separately check MLAS
transpose results, including two-thread execution. Runtime inference remains
a separate installed-API scenario.
