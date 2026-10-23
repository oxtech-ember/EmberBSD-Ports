# libei 1.6.0 source-analysis scope

Origin: EmberBSD (AI-assisted).

The reviewed cross build uses GCC 16.2.0 and an EmberBSD 11 AArch64 sysroot.
The real Meson compilation database supplies each source configuration.
The baseline has 117 C, header and protocol inputs identical to the pinned
upstream archive. The munit patch changes only test-library packaging.
The `nb1` runtime delta is confined to `src/brei-shared.c`.

The scope contains 20 compilation units, including the two configurations of
`brei-shared.c`. It covers the libei/libeis contexts, connection, handshake,
socket and descriptor handling, libeis client handling, both generated protocol
units, liboeffis, and util IO, memfile, memmap and event sources.
Other device classes, demo tools, Python code and dependency internals are
outside this source-analysis scope.

Preserve `compile_commands.json`, generated headers and `config.h` with the
source snapshot. Resolve its relative paths against the actual build directory.
When calling the real cross compiler directly, apply the pkgsrc wrapper's
sysroot mapping to explicit `/usr/include` and `/usr/pkg/include` paths.
Keep source macros and language flags. Remove only output/dependency-file
options before selecting a private analysis output.

Run GCC with `-fanalyzer -Wanalyzer-too-complex -c -o /dev/null` and retain
all diagnostics. GCC16 no longer supports `-fdiagnostics-format=json`; use
text or its documented SARIF output. Run Clang 23 Static Analyzer with
`--target=aarch64--netbsd11.0 --analyze -Xanalyzer -analyzer-output=text`.
Retain target includes and macros. Omit only GCC-specific warning switches
that Clang does not implement, and record that option mapping.

Cppcheck 2.22 examines the actual GCC-preprocessed translation units with
`--language=c --std=c11 --platform=unix64 --library=posix`
and `--enable=warning,style,performance,portability --error-exitcode=1`.
The GCC preprocessor retains target headers and macros, including NetBSD ABI
identifiers. Keep the original source line markers in these inputs.

## Findings and limits

The 20 GCC and 20 Clang invocations complete. They do not produce a clean
whole-scope result. GCC reports complexity limits and inherited ownership
findings in descriptor and refcount cleanup. Clang also reports cleanup,
refcount and null-pointer-arithmetic findings. These need separate review
by the libei Ports maintainer against the upstream lifetime contracts.
They are not confirmed new regressions or suppressed findings.

The length arithmetic defect is confirmed and fixed in `nb1`.
After that fix, GCC's reported out-of-bounds sites in each `brei-shared.c`
configuration decrease from four to two. The remaining reports interpret
`str[slen - 1]` as a huge positive offset despite the preceding `slen != 0`
branch and allocation of exactly `slen` bytes. This is a symbolic unsigned
subtraction limitation. The logs retain these reports without suppression.

Cppcheck cannot parse some GNU list and object macro expansions. Its remaining
reports include errno side effects through NetBSD's `__errno()` accessor,
intentional `assert(!"message")` expressions, and inherited style findings.
These results do not establish a clean Cppcheck pass for the full library.
The changed arithmetic helper separately passes Cppcheck and Clang analysis
and its actual-source ASan/UBSan boundary regression.

The source checks establish no Valgrind, target runtime, portal or compositor
result. Run the compiled upstream test bundle on the matched target separately.
