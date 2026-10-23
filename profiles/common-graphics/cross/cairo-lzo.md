# Cairo script LZO bounds

The common Cairo 1.18.6nb1 recipe keeps LZO enabled. Three script consumers
now call `lzo2a_decompress_safe`: compressed files, font data and raw images.
Each call supplies the allocated output capacity and requires the declared
output size. File and font allocation paths reject sizes outside the internal
`int` allocator interface before narrowing or adding a string terminator.
The file path also releases its slab object if string allocation fails.

The two local patches use the upstream LZO 2.10 safe API. They were prepared
with AI assistance and independently reviewed. They are not upstream commits.
The source archive and patch hashes are in the [recipe distinfo](../../../pkgsrc/graphics/cairo/distinfo).
Upstream sources: [Cairo releases](https://cairographics.org/releases/) and
[LZO](https://www.oberhumer.com/opensource/lzo/).

## Focused regression

The [Python runner](../tests/cairo-lzo-bounds.py) extracts the three complete
production functions without rewriting them. Its C fixture uses real LZO
compression/decompression and Cairo image surfaces. Guarded allocation adapters
retain the real allocator's `int` interface and inspect the output red zones.
They do not replace the decoder. This is a focused function check, not a full
script parser or package test.

Use the verified release tree and a separate copy with the recipe patches.
Supply current Cairo and LZO development libraries through `pkg-config`.
Use a new output directory for each run:

```sh
python3 profiles/common-graphics/tests/cairo-lzo-bounds.py \
  --source /absolute/cairo-source --output /absolute/check-output \
  --cc /absolute/gcc-16 --sanitize --analyze
```

The runner accepts `--cflags` and `--pkg-config` for explicit dependency inputs.
For cross compilation, supply the GCC16 target compiler and target pkg-config
wrapper. `--compile-only` leaves the binary for target execution. Alternatively,
`--runner` supplies a command prefix that can execute the binary on the target.
A compile-only result does not establish runtime acceptance.

GCC 16.2.0 on macOS arm64, with ASan/UBSan and guarded allocations, produced:

| Cases | Original | Patched |
| --- | ---: | ---: |
| Valid data, oversized output, short output, truncation and trailing bytes in all three paths | 9/15 | 15/15 |
| INT_MAX, UINT32_MAX and negative decoded sizes in file/font paths | 0/6 | 6/6 |
| String allocation failure and slab ownership | 0/1 | 1/1 |
| Total | 9/22 | 22/22 |

The original functions overwrite guard bytes for oversized output and accept
short output. The patched functions reject both and retain valid contents.
GCC `-fanalyzer` reports no findings in this focused harness. This does not
establish clean analysis of all Cairo sources. Clang Static Analyzer 23.1.4
reports one inherited slab leak before the fix and none after it. The
allocation-failure regression confirms the repair.

## Cppcheck with the compiler context

Use the same source and GCC16 dependency inputs as the focused build:

```sh
python3 profiles/common-graphics/tests/cairo-lzo-bounds.py \
  --source /absolute/cairo-source --output /absolute/cppcheck-output \
  --cc /absolute/gcc-16 --cppcheck /absolute/cppcheck
```

This mode does not build or run an executable. GCC preprocesses the complete
fixture and the three unchanged production functions with the real headers.
The runner records the macro dump, header search, commands and preprocessed
SHA256. It derives the Cppcheck platform from GCC type-size macros and verifies
every size and plain-char signedness with GCC static assertions. This also
works with explicit cross-compiler and target pkg-config inputs.

Cppcheck 2.22.0's standard model defines `errno_t` as the macro `int`.
That substitution corrupts a real `typedef int errno_t;` declaration.
`-Uerrno_t` prevents this substitution only when analyzing the already
preprocessed file. No header, production declaration or diagnostic is removed.
GCC preprocessing also resolves LZO's compiler and limits macros directly.

The paired macOS ARM64/GCC 16.2.0 analysis completes with zero errors,
zero warnings and the same eight style findings on both versions. Three
findings concern system-header functions. The others concern constness,
an identity bit-order adapter in the fixture and a fixture buffer assignment.
The informational checker report is also retained. Exhaustive branch checking
is enabled. No parser failure or branch-limit notice remains.

`cppcheck.xml`, `cppcheck.stdout` and `cppcheck-result.json` retain all findings.
The process returns Cppcheck's status unchanged: it returns 1 for the retained
style findings because `--error-exitcode=1` is enabled. This result establishes
completed analysis and no new findings in the focused scope. It does not claim
an entirely clean report or analysis of every Cairo translation unit.

Valgrind is unavailable on this macOS host. ASan/UBSan and allocation guards
provide separate memory checks. LeakSanitizer exit handling is unavailable on
this host; the check uses `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and makes
no complete leak-detection claim. Target package build, installation and full
Cairo script interpreter execution remain unverified by this check.
