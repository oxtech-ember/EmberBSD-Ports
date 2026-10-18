# Lerc Huffman padding and package validation

The common graphics profile uses the canonical `graphics/lerc` provider,
updated to 4.2.0nb1. It retains the upstream shared-library ABI and pkgsrc
license, installation list and build options. [sources.tsv](../sources.tsv)
pins the official Esri archive. This is also a dependency of the common TIFF
provider used by OCCT image support.

## Memory correction

The original `fpl_EsriHuffman::EncodeHuffman` reserves one extra unsigned
integer so the decoder can read ahead. `Huffman::PushValue` initializes each
data word, including its unused bits. It does not initialize the extra word.
The returned stream includes that word, and the outer Lerc2 checksum covers it.

The patch initializes only the extra word before advancing the output pointer.
It preserves the code table, data words, stream size, decoder and library ABI.
The allocation already includes this word. The original Apache-2.0 license
and authorship remain in the source. The adaptation is AI-assisted.

## Reproduce the upstream execution check

Build normal native and GCC16 cross packages with the common tools.
Compile the unmodified upstream `src/LercTest/main.cpp` against each selected
package's headers and shared library. For the native run, verify the loaded
library path before running Memcheck. Use an explicit package or stage library
directory if the build host has another installed Lerc.

```sh
"$HOST_CXX" -std=c++17 -O2 -g "$SOURCE/src/LercTest/main.cpp" \
    -L"$NATIVE_LIBRARY_DIR" -Wl,-rpath,"$NATIVE_LIBRARY_DIR" \
    -lLerc -o "$WORK/lerc-upstream"
"$WORK/lerc-upstream" </dev/null
valgrind --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=all --track-origins=yes --error-exitcode=99 \
    "$WORK/lerc-upstream" </dev/null
```

The upstream source uses its adjacent public headers. Verify those headers
match the selected package. The four samples check masked float data, RGB
bytes, lossless multi-band floats and no-data values. The process returns
nonzero on a numerical or metadata failure. No replacement test is used.

## Current evidence

On Linux amd64 with GCC16.2, all four original samples pass before and after
the patch. Valgrind 3.24 reports one uninitialized conditional in the baseline
lossless-float decode, traced to the Huffman allocation. The patched ordinary
package stage passes with zero errors and zero live allocations, without
suppressions. Independent review confirms the write stays inside the existing
allocation for both a complete and a partial final data word.

Normal native and AArch64 package file, permission, RELRO, RPATH and work-path
checks pass. The target package also passes its PIE check. Its installed SDK
payload matches all packing-list checksums and symlink targets. The upstream
AArch64 consumer links to `libLerc.so.4` and the common GCC16 runtime, using
only target runtime paths. Its execution in EmberBSD remains pending.

Clang 19 Static Analyzer reports no diagnostics in the actual changed
translation unit, before or after the patch, for native and AArch64 inputs.
Cppcheck 2.22 cannot finish those same real preprocessed inputs: GCC16
`type_traits` fails its native parser, and target `string.h` fails its target
parser. No Cppcheck-clean or whole-library analysis result is claimed.

The exporter retains the exact archive and patch checksums. Its preflight
rejects a missing recipe, changed archive pin and an omitted patch/checksum.
Full KiCad, TIFF and OCCT acceptance are separate checks.
