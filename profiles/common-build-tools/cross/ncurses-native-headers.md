# Native headers for ncurses cross generators

The common ncurses 6.6nb1 recipe configures host generators separately.
The library still uses target GCC16 and target configure results.
The build-role revision does not change the public ABI or dependency bounds.
An accepted native ncurses 6.6 tool still meets the existing tool predicate.

Upstream `make_hash` and `make_keys` include `build.priv.h` with
`USE_BUILD_CC`. The original header selects target `ncurses_cfg.h` even
when `BUILD_CC` selects the host compiler. On Darwin, the target result
`HAVE_MALLOC_H=1` then requires a missing native `malloc.h`.
Adding a native include directory at the end does not fix that selection.

The cross `pre-configure` hook calls the ordinary native pkgsrc configure
target in a private object directory. `env -i` separates recursive make
variables, compiler environment, configure site and cache state. The recipe
retains native pkgsrc compiler policy. It does not invent header answers.
The hook generates native headers and copies three exact files to private
names. Only `USE_BUILD_CC` together with `NCURSES_BUILD_HEADERS` selects
these names. Native builds and target library compilations retain their
original include paths. The recipe reads `BUILD_CPPFLAGS`, `BUILD_CFLAGS`,
`BUILD_LDFLAGS` and `BUILD_LIBS` from the real native generated Makefile.

Nested generic headers can open the target header filenames. The native
configuration and include guards must already be active. The regression
compares complete active macro sets to verify this boundary. It does not
infer correctness from include filenames alone. A missing private header
fails compilation instead of falling back to target configuration.

## Reproduce the bounded checks

Use a prepared common profile, its make configuration and a configured
ncurses target source tree. All native dependency predicates must already
be satisfied. The test refuses a new dependency installation.
Use a new absolute output directory for each command.

```sh
BMAKE=/absolute/host/bin/bmake python3 \
    profiles/common-build-tools/tests/ncurses-native-headers.py \
    /absolute/export /absolute/mk.conf /absolute/target-ncurses-source \
    /absolute/new-header-check
python3 profiles/common-build-tools/tests/ncurses-export-guard.py \
    /absolute/new-export-preflight-check
```

The Darwin header test executes the canonical recursive hook. It poisons
outer make variables, compiler selection, configure site and cache values.
It captures the actual configure environment and checks native compiler
flags. An owned target-header overlay receives the actual source patch.
The candidate retains production target-first include order. Removing its
role guard must restore the `malloc.h` failure, even with native flags.
The original generators must fail on `malloc.h`. Both repaired
generators must compile. Three capability tables and the key table must
match ordinary native output byte for byte. Include traces, complete macro
sets, absent-private-header refusal and unchanged target input hashes are
also checked. Missing `CONFIGURE_ENV` must fail. The export test runs the
actual common-tools preflight block and removes the required delta in its
private fixture. It does not claim a complete new export.

## Analysis and acceptance boundary

Cppcheck 2.18.0 checks both actual generator units after preprocessing with
the native compiler and real generated headers. Its C11 model covers the
C17 core syntax used here. Native and repaired inputs differ only in empty
preprocessor lines. Neither input has a parser or error-severity finding.
Both retain the same five `invalidPrintfArgType_sint` warnings in
`make_hash.c`, plus inherited condition, scope and unused-header diagnostics.
The unsigned generated counts fit both signed and unsigned integer ranges.
This header-role change does not alter that upstream formatting code.
No finding or category is suppressed.

GCC 16.2.0 `-fanalyzer` and Apple Clang 21 Static Analyzer report no findings
for either unit with both header selections. GCC analysis retains the real
native macros and includes. It removes the Clang-only `-no-cpp-precomp`
option and uses the installed macOS SDK explicitly.

Native GCC16 ASan/UBSan passes eight real generator invocations with exact
output comparison, failure-on-error options and no sanitizer diagnostics.
Leak checking remains unverified. LeakSanitizer deadlocks during process
exit on this Darwin 27 AArch64 host, including an empty program. The
successful ASan/UBSan runs explicitly use `detect_leaks=0`. Valgrind does
not support this host. These runs do not establish leak acceptance.

Upstream cross-run fallbacks for C++ `override` and parameter initialization
remain unchanged. The `unsigned char` Boolean representation follows the
existing compile-proven `sizeof(bool)=1` result. No new cache answer is added.
Full target packaging, ncurses runtime and consumer acceptance are separate.
