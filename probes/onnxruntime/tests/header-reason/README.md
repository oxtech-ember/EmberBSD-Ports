# Installed C header and enum ABI control

The upstream 1.31.0 C header initializes the UNKNOWN incompatibility flag with
`1 << 31`. Shifting a signed 32-bit C value into that position has undefined
behavior. It is also not a valid C integer constant expression.

The port uses `(-2147483647 - 1)`. This preserves the existing signed C++ enum
value, its `int` underlying type, four-byte size, four-byte alignment, and
layout in a containing struct. Conversion to the API's `uint32_t` reason mask
still gives `0x80000000`. The three lower flags keep their original values.
An unsigned shift would change the C++ enum's value and underlying signedness.

```sh
cmake -S probes/onnxruntime/tests/header-reason -B /absolute/header-controls \
  -DONNX_RUNTIME_INCLUDE_DIR=/absolute/installed/include/onnxruntime \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build /absolute/header-controls --parallel 1
ctest --test-dir /absolute/header-controls --output-on-failure
```

Use the runtime's CMake toolchain for an EmberBSD cross build. Run both target
executables in EmberBSD. They print the signed value, enum width, containing
layout, and unsigned mask. Static assertions verify all of those properties.

With pristine upstream headers, the strict C17 build must fail on the signed
shift and integer constant expression. Both old and patched headers pass the
C++20 ABI assertions. The patched C header passes strict C17 compilation.

Cppcheck can compare the actual compiler's preprocessed C inputs. Preserve
line markers and use the measured target platform. This removes alternate
preprocessor configurations without header substitutes or suppressions. The
baseline reports `shiftTooManyBitsSigned`; the patched input does not.
This control checks a public header and its ABI. It does not run inference.
