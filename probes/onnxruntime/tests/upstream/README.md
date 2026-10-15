# Selected ONNX Runtime upstream tests

This helper compiles seven unchanged upstream test translation units. Their
shared MLAS test header uses the canonical NetBSD guarded-buffer patch.
It declares future read/write permissions for PaX while keeping guard pages
inaccessible, and checks POSIX `MAP_FAILED`. The
[guard controls](../mlas-guard) test both causes. The helper uses the real
runtime build's static archives. It does not substitute a standalone MLAS
implementation or disable runtime thread support.

The selected controls cover narrowing, checked products, string parsing, UTF8,
convolution working-buffer overflow, and matrix transpose. The upstream MLAS
main registers short transpose fixtures, including real two-thread cases.
The CPU profile with exception support registers 76 tests. Each transpose
fixture checks all matrix dimensions from 1 through 32 against an independent
reference.

Wait until the runtime build finishes. Then create its archive targets from
the same completed production objects:

```sh
cmake --build /absolute/runtime-build \
  --target onnxruntime_common onnxruntime_mlas --parallel 1
cmake -S probes/onnxruntime/tests/upstream -B /absolute/upstream-tests \
  -DORT_SOURCE_DIR=/absolute/patched-onnxruntime \
  -DORT_BUILD_DIR=/absolute/runtime-build \
  -DGTEST_SOURCE_DIR=/absolute/verified-googletest \
  -DCMAKE_PREFIX_PATH=/absolute/eigen-prefix \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build /absolute/upstream-tests --parallel 1
ctest --test-dir /absolute/upstream-tests --output-on-failure
```

Use the compiler, toolchain, source revision, dependency archives, and sysroot
from the runtime build. The helper imports production ThreadPool definitions
and RTTI settings from its compilation database. It requires the common and
MLAS archives and records every linked archive path. It does not fetch inputs.
Use the profile's verified GoogleTest source.

For a cross build, pass the runtime's CMake toolchain. Run the resulting
`onnx-upstream-controls` executable in EmberBSD. A native build can run under
strict Memcheck on a supported host.

This is a selected internal upstream suite. It does not test the installed
C/C++ API, every CPU operator, external model accuracy, accelerators, or boards.
Those need separate acceptance scenarios.
