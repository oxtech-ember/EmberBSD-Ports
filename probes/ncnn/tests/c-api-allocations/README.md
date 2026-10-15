# C API allocation, lifetime and callback controls

This control compiles the actual upstream and patched `src/c_api.cpp`.
It links both objects to the installed ncnn C++ runtime. GNU linker's
`--wrap=malloc` fails the next direct wrapper allocation exactly once.
C++ runtime allocations still use their real allocator. No ncnn function,
constructor, graph operation or syscall is replaced.

All 13 wrapper allocation sites are tested. The baseline runs each failure
in a child and requires `SIGSEGV`. The patched program requires a null handle
for handle factories. Failed custom-layer registration must leave its list
unchanged and log an error. These registration functions return `void`, so
they cannot report a status code. The model must reject the unregistered
custom type. Registration and model loading must work when retried.
Both preallocated layer factories must
delete their C++ layer when the wrapper allocation fails.

```sh
cmake -S probes/ncnn/tests/c-api-allocations -B /absolute/allocation-tests \
  -DCMAKE_PREFIX_PATH=/absolute/sdk \
  -DNCNN_SOURCE_DIR=/absolute/verified-patched-source \
  -DNCNN_BASELINE_SOURCE_DIR=/absolute/verified-original-source \
  -DNCNN_CONFIG_DIR=/absolute/runtime-build
cmake --build /absolute/allocation-tests --parallel 2
ctest --test-dir /absolute/allocation-tests --output-on-failure
valgrind --tool=memcheck --track-origins=yes --leak-check=full \
  --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
  /absolute/allocation-tests/ncnn-c-api-allocations-after
```

The patch guards wrapper `malloc` failures. The upstream throwing-`new`
policy remains in force. Failure of a later C++ allocation can still throw;
this control does not establish a general C API out-of-memory guarantee.

The lifetime control tests `ncnn_modelbin_create_from_mat_array`. The upstream
adapter retains a pointer into a destroyed local vector. Its negative control
loads one weight through the actual unmodified C API under Memcheck:

```sh
valgrind --tool=memcheck --track-origins=yes --leak-check=full \
  --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
  /absolute/allocation-tests/ncnn-c-api-lifetime-before --baseline-first
```

That command must return 99 with invalid accesses to the released array.
The patched adapter owns its vector of reference-counted matrices. Its control
destroys all original handles before loading six arrays through the 1D, 2D and
3D callbacks. It checks all 48 values, empty and exhausted input, and user
callback dispatch. Run `ncnn-c-api-lifetime-after` under the same strict
Memcheck options; it must return zero with no errors or retained allocations.

The callback controls exercise the actual C++ adapters behind the C handles.
They check 18 cases: single and vector forwarding, errors with missing or
partial outputs, successful output, missing successful output, zero-sized
forward and inplace arrays, and null results from all six ModelBin callbacks.
Nonzero callback status must survive unchanged. Failed calls must preserve
destination matrices and release every returned owned handle. Missing output
from a successful callback must return `-100`. Null weight results must become
empty matrices.

`ncnn-c-api-callbacks-before --baseline` requires 13 original failures as
`SIGSEGV` or changed destination values. `ncnn-c-api-callbacks-after` checks
the repaired paths. Run the latter with the same strict Memcheck options.
The zero-sized array controls check the actual callback arguments; they do
not constitute a separate UBSan check of the original reference expressions.

The harness builds six programs and registers five CTest cases. The original
lifetime negative control is run separately under Memcheck. The header-only
[C visibility and layout controls](../c-api-header/README.md) are separate.
