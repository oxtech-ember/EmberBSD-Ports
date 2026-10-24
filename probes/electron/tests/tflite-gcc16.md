# TFLite GCC16 checks

The AI-assisted `chromium-tflite-explicit-arithmetic-gcc16.patch` changes three
production files in the pinned TFLite source. Apply it from the Chromium root
with `patch -p1 -F0`, after the selected DEPS and NetBSD adaptations.

The strided-slice condition gains parentheses around its two comparisons.
Relational operators already bind before `!=`; this expresses the same parse.
Scatter multiplication explicitly casts its product to `DataType`, the existing
destination type. The reduction product explicitly casts its product to `T`,
the existing return type. Both retain operand order, integer promotions and the
conversion that assignment or return already required. Bool still uses its
0/1 product conversion. Eigen half multiplication already returns half by value;
the same-type cast introduces no extra rounding. No short-circuit operation,
new numeric mode, overflow policy or compiler diagnostic change is introduced.

Replay the complete production GCC16 commands for these files:

- `third_party/tflite/src/tensorflow/lite/kernels/strided_slice.cc`
- `third_party/tflite/src/tensorflow/lite/kernels/stablehlo_scatter.cc`
- `third_party/tflite/src/tensorflow/lite/kernels/reduce.cc`

All three baselines fail: one comparison-grouping diagnostic and four bool
context diagnostics. All three patched commands compile with unchanged flags.
All six paired preprocessing and Clang Static Analyzer checks complete.
Clang diagnostic signatures match across each pair. Cppcheck stops at unchanged
parser errors in all six inputs; this is incomplete analysis.

Existing negative-stride, offset, scatter multiplication and constant/dynamic
reduction product tests were inspected. They were not executed. The patch does
not change SVDF or any scratch-buffer alias contract. These focused compile
and analysis checks do not establish a complete runtime or browser build.

## Hybrid SVDF scratch contract

The AI-assisted SVDF patch passes null for the integer GEMM scratch argument
in the existing call with a null CPU backend context. The float output buffer
remains unchanged and no longer aliases an integer argument. The selected
thirteen-argument portable and SSE implementations do not use that integer
scratch. The NEON implementation uses it only in non-null-context branches;
its null-context fallback has no integer scratch argument. Other overloads
that require scratch are unchanged. No restrict annotation is weakened and
no additional buffer is allocated.

The actual production `svdf.cc` GCC16 command fails on the original alias and
compiles after the patch, with unchanged diagnostics and libc++ configuration.
Both Clang Static Analyzer calls complete with the recorded inherited results.
Both Cppcheck inputs stop at dependency parser limits.

The [standalone numerical fixture](svdf-correctness.cc) uses the actual
`EvalHybridSVDF` header. Compile it together with these pinned source files
from `tensorflow/lite/kernels/internal/`:

- `tensor_utils.cc`
- `reference/portable_tensor_utils.cc`
- `runtime_shape.cc`
- `portable_tensor_utils.cc`

Use the common target GCC16 and matching sysroot. This standalone executable
uses static common libstdc++ and libgcc; it does not use production Chromium's
libc++ ABI. No mathematical implementation is replaced with a test stub.
The selected AMD64 profile defines SSE3 but not SSSE3 or NEON and therefore
selects the real portable dispatcher. Twelve calls cover symmetric and
asymmetric quantization, zero input, cached row sums, rank two, two batches,
state history, bias, Relu6, finite values and buffer guards. All independent
expected values pass on physical NetBSD 11 AMD64.

All five source files were also compiled with `-fsanitize=undefined`,
`-fno-sanitize-recover=all` and `-fsanitize-trap=all`. The same twelve calls
pass on the target. The [volatile bounds fault](ubsan-bounds-fault.cc) compiled
with the same instrumentation terminates with SIGILL, status 132. An explicit
waiting shell records that status with core dumps disabled. Direct SSH signal
reporting alone was not accepted as proof. Both executables need only target
libm and libc, so no sanitizer runtime package was installed.

The current [Valgrind supported profiles](https://valgrind.org/info/platforms.html)
do not include modern NetBSD AMD64 or Darwin ARM64. This bounded UBSan run is
not Valgrind or ASan. Static C++/GCC libraries and system libraries remain
uninstrumented. Other architecture paths have source review, not runtime
execution. These checks do not establish complete TFLite or browser acceptance.
