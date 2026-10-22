# Native headers for ncurses cross generators

The common ncurses 6.6nb3 recipe configures host generators separately.
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

The cross configure environment selects the native `TIC` by its absolute
path for configure queries. Upstream substitutes `TIC` into the lowercase
`tic_path` default in `run_tic.sh`; uppercase `TIC_PATH` does not select that
default. The database writer must also match the target filename layout.
Darwin's ordinary native provider writes hexadecimal leaf directories.
A target with `MIXEDCASE_FILENAMES=1` reads single-character directories.
The same compiled entry can be valid while its installed path is unreadable.

After target configure, the recipe preprocesses the actual target header.
A second private native object directory builds `tic` from the same source.
Its explicit internal `EMBERBSD_NCURSES_TIC_LAYOUT=character|hex` role changes
only the documented mixed-case configure switch. Other native pkgsrc policy
stays active. Ordinary native builds keep their platform default. The role
refuses invalid modes and cross compilation. Character mode requires a
case-sensitive build filesystem. No dependency may be installed implicitly.

The recursive make names `configure` explicitly before its private build
target. The pkgsrc barrier can then forward the fresh configure phase.
A configure prerequisite alone can leave the barrier target list empty and
start the default full native build. The ordinary `BUILD_MAKE_CMD` retains
native compiler and linker wrappers for both private build commands.
The upstream `progs/tic` target builds the private library it needs. Its real
upper- and lower-case alias probe must produce the target directory layout.
Only then does an explicit strict SUBST class retarget the configured
`run_tic.sh` to that absolute private provider. The earlier native generator
headers keep their separate configuration. The target reader and its normal
layout stay unchanged. No target executable generates the database.
This follows the incompatible-layout warning in upstream `INSTALL`, in its
cross-compilation section.
A strict cross-only substitution gives the installed `ncurses6-config` helper
its target `/bin/sh` interpreter. Build-time `CONFIG_SHELL` stays native.
The cross-only upstream `--disable-pkg-ldflags` option omits build-only link
paths from the helper and all five pkg-config files. It does not change
library build flags, compiler feature defines or native configuration.

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
python3 profiles/common-build-tools/tests/ncurses-install-tic.py \
    /absolute/before/misc/run_tic.sh /absolute/after/misc/run_tic.sh \
    /absolute/native-prefix /absolute/new-install-tool-check \
    --tic-provider /absolute/private-native-source/progs/tic \
    --target-cfg /absolute/target-ncurses-source/include/ncurses_cfg.h \
    --target-config /absolute/stage/bin/ncurses6-config \
    --target-metadata-dir /absolute/stage/lib/pkgconfig \
    --producer-path /absolute/build-sysroot
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

The install-tool test takes actual configured scripts before and after the
recipe change. Only the native tic default may differ. The baseline can
use bare `tic` or the absolute ordinary native provider. A hostile PATH tool
must expose bare selection and must stay unused after the fix. Select the
private writer with `--tic-provider`; the default is `native-prefix/bin/tic`.
The real provider compiles the ordinary native extended `scrt` entry. The
output path must match the actual target header selected by `--target-cfg`.
The ordinary native writer must fail this guard when its layout differs.
Native `infocmp` decodes the exact output bytes through upstream
`TERMINFO=hex:` quickdump. Its `$TERMINFO` marker must exclude database
fallback, and the capabilities must match. The check does not rename the
installed database to claim target acceptance. Actual target `infocmp` must
read the original installed leaf through the runtime runner separately.
The actual target helper passes version,
prefix, ABI, no-argument and unknown-option calls under POSIX sh. All three
upstream shell references use the target interpreter.

Select the five actual staged pkg-config files with `--target-metadata-dir`.
Pass each physical producer prefix with `--producer-path`. The helper body,
consumer flags and pkg-config files must omit these paths. The native prefix is
also forbidden when it differs from the logical target prefix. Do not select
the logical target prefix as a producer path.
The helper must retain its target feature defines, include paths and library.
The test preserves hashes of the selected native tools and helper. An actual
old metadata stage must fail this producer-path guard.

The normal configure producer comparison separately verifies that the option
changes only exported link flags. Build `LDFLAGS`, `EXTRA_LDFLAGS`, compiler
feature flags and native configuration remain unchanged. These are host
metadata checks. They do not establish target runtime acceptance.

## Numeric reader regression

The actual instrumented reader exposed a separate upstream numeric-shift
error. Integer promotion made an input byte signed before the shift by 24.
The source patch converts each input byte to unsigned before all three
numeric assembly shifts. Numeric widths, sign extension and absent/cancelled
sentinels remain unchanged. The patch applies to native and target readers.

`tests/ncurses-read-numbers.c` includes the selected complete `read_entry.c`.
Define `EMBERBSD_NCURSES_READ_ENTRY_SOURCE` to its quoted absolute filename.
Use the configured native extended-number headers, actual compile flags and
library. Build with `-fsanitize=address,undefined` and run with failure-on-error
options. Run against the exact upstream source and the patched source.
Six 16-bit and nine 32-bit values cover zero, signed limits, wider positive
values and both sentinels. The upstream input must fail UBSan; all 15 patched
values must match. Keep the selected source, compiler, flags and library hashes.

Both actual native layouts also compile the real `scrt` entry. The exact
compiled bytes that failed before must decode after the repair. Recompiling
the entry must preserve its bytes and capabilities. These checks do not use
an alternative numeric decoder or disable sanitizer checks.

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

The later numeric reader change has a separate executed scope. The complete
instrumented native library, `tic` and `infocmp` preserve both native layouts.
The same real entry fails UBSan before the repair and decodes after it.
The numeric source test also fails before and passes all 15 values after it.
ASan/UBSan remains enabled. The earlier leak-checking limitation still applies.

Cppcheck 2.22.0 rejects the valid macOS SDK `errno_t` typedef, including a
two-line control. Its whole-unit result remains unqualified. Existing
Cppcheck 2.18.0 supplies additional reader/writer coverage with inherited
style, portability and null-check warnings retained. The Clang-preprocessed
`tic` unit also uses unsupported Apple block syntax; its additional 2.18.0
run uses the real native GCC16 preprocessor and SDK explicitly. These inputs
have different compiler builtins. They do not establish a clean current-tool
result. GCC16 and Clang analysis of the changed reader retain their actual
configured headers and flags. Unrelated `tic` allocation-failure findings and
whole-program memory acceptance remain separate work.

Upstream cross-run fallbacks for C++ `override` and parameter initialization
remain unchanged. The `unsigned char` Boolean representation follows the
existing compile-proven `sizeof(bool)=1` result. No new cache answer is added.
Full target packaging, ncurses runtime and consumer acceptance are separate.
