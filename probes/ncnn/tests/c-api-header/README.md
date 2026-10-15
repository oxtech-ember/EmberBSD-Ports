# Strict C headers and C/C++ layout

The ncnn 20260526 C API puts `NCNN_EXPORT` on four structure type declarations.
GCC16 ignores the visibility attribute on C structure types. A strict C consumer
fails with four `-Werror=attributes` diagnostics. The installed CMake target
marks its includes as system headers and hides these warnings. The ordinary
`-I` from the installed `ncnn.pc` file exposes the defect.

`patch-c-api-type-visibility` keeps the original C++ type declarations. It omits
only their type visibility attribute in C. All function export declarations
remain unchanged. This does not change the structure fields or their layout.
The repair is local and AI-assisted. It has not been accepted upstream.

The Ruby harness uses actual installed `pkg-config --cflags ncnn`. It adds an
ordinary `-I` before those flags to select the original or repaired header.
It copies the installed `platform.h` and `ncnn_export.h` without edits. Neither
header directory is marked as a system include. The compiler must be GCC16.
It uses strict C11 and C++17, with `-Wall -Wextra -Wpedantic -Werror`.

```sh
ruby probes/ncnn/tests/c-api-header/run.rb \
  --prefix /absolute/installed/sdk \
  --baseline-header /absolute/original/ncnn/src/c_api.h \
  --patched-header /absolute/installed/sdk/include/ncnn/c_api.h \
  --work /absolute/new/header-controls \
  --cc gcc --cxx g++ --objcopy objcopy --run
```

The work directory must be new or empty. All outputs, diagnostics, exact
commands, header hashes and the result receipt stay there. `--run` executes
native layout programs. Omit it when cross-compiling. Set `--cc`, `--cxx`,
`--objcopy` and `--readelf` to the cross tools where needed. Keep the configured
EmberBSD sysroot in the compiler environment.

The unmodified C header must fail on exactly four ignored type visibility
attributes. The original C++ header, repaired C header and repaired C++ header
must compile without a diagnostic. For all four affected structures, the
control records size, alignment and every field offset. The compiler emits
these values in a `.ncnn_abi` object section. `objcopy` extracts the section;
all three byte sequences must match. This also checks a cross target without
running its code. On a native host, the three executable outputs must match.
The cross-built layout programs can also run on EmberBSD.

The control builds two representative API function definitions in shared
libraries with `-fvisibility=hidden`. Their public declarations must still
export both functions with `GLOBAL DEFAULT` visibility. A complete header
comparison then reverses only the four conditional type declarations. Every
other byte must equal the original header, including all function exports.

This is a header and layout regression. It does not execute inference or
establish that other ncnn C APIs are safe. The separate runtime and application
controls cover those scenarios.
