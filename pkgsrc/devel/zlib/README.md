# zlib 1.3.2

Use the current stable release listed at <https://zlib.net/> on 2026-10-18.
Upstream released this version on 2026-02-17. The archive SHA256 is
`d7a0654783a4da529d1bb793b7ad9c3318020af77667bcae35f95d0e42a792f3`.
The common source manifest and pkgsrc `distinfo` verify the original archive.

This recipe derives from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`, `devel/zlib`.
Keep its authorship, package metadata and upstream zlib license.
The exporter replaces the vendored 1.3.1 sources with the verified release.
The original pkgsrc Libtool Makefile retains `-version-info 1:2` and the
existing NetBSD library naming. All fifteen library sources remain enabled,
including the gzip file API. No replacement SONAME links are fabricated.
The buildlink floor requires this repaired common provider.

## Source adaptations

| Patch | Reason |
| --- | --- |
| `gzguts.h` | Retain the original pkgsrc `<unistd.h>` declaration include. |
| `gzlib.c` | Initialize `past` for writers, since seeking and position queries read it in both modes. |
| `gzwrite.c` | Allocate the input buffer before a deferred seek writes zero bytes. A seek can precede the first `gzputc`. |
| `zconf.h` | Test `HAVE_UNISTD_H` and `HAVE_STDARG_H` with `defined()` first. Consumers built with `-Werror=undef` accept the installed header. |

The `gzlib.c`, `gzwrite.c` and `zconf.h` changes are AI-assisted EmberBSD fixes. They have not been
submitted upstream. The first patch preserves the existing pkgsrc adaptation.
The `zconf.h` change keeps the upstream selection: an undefined or zero name
leaves `Z_HAVE_UNISTD_H` or `Z_HAVE_STDARG_H` unset. It changes no library
object, so the buildlink floor stays at nb1. Run
`CC=/absolute/cc sh tests/zlib-wundef.sh /absolute/distfiles /absolute/new-work`
from `profiles/common-build-tools`; it fails with the unchanged header.
No compression, gzip, append, seek or error behavior is disabled.

`files/seek-writer.c` tests deferred writer seeks, position queries, zero
fill, append, concatenated gzip members and invalid handles. Compile it with
the selected provider's headers and library. Execute the target binary in
EmberBSD; use the native binary for Memcheck on a supported host.

```sh
"$CC" -std=gnu23 -O2 -g -Wall -Wextra -Werror \
    -I"$provider/include" files/seek-writer.c \
    -L"$provider/lib" -Wl,-rpath,"$provider/lib" -lz -o "$work/seek-writer"
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=all --track-origins=yes --error-exitcode=99 \
    "$work/seek-writer" "$work/writer.gz"
```

The output path must be private to the test. The first write truncates it.
Check the loaded library before treating the result as provider acceptance.

## Validation boundary

Native Linux x86_64 GCC 16.2.0 builds both upstream shared and static
libraries. All 18 upstream CMake tests pass with the matching GCC16 `gcov`.
An initial attempt with host `gcov` 14 fails the coverage-summary test;
that tool mismatch is retained as a failed attempt, not a library failure.
The exported recipe builds a native package with GCC16 and Libtool 2.6.2.
Normal PLIST, permission, RELRO, RPATH and work-reference checks pass.
Installation into an isolated root passes the focused consumer under strict
Memcheck. Its build receipt records Linux/x86_64 and `CC_VERSION=gcc-16`.
These checks use the native Linux/x86_64 provider.

Strict Valgrind 3.24 Memcheck exposes an uninitialized branch in the unchanged
upstream example. The focused regression exposes 50 errors in 16 contexts
against upstream. The `past` repair removes 6 contexts, while the remaining
10 expose the uninitialized seek buffer. The complete series passes the
upstream example, focused regression and a 131072-byte binary gzip roundtrip
with zero errors, zero remaining heap blocks and no suppressions.

Cppcheck 2.22 uses the actual native compilation database, GCC16 predefined
macros, C23, the Unix64 platform, POSIX models and every diagnostic category.
The comparison covers 37 compiler configurations in each source tree.
The baseline has 144 diagnostics: 110 style, 2 warnings and 32 information
messages. The complete series has the same findings and one additional
missing-system-header message for the retained `<unistd.h>` include.
Neither tree has an error-severity diagnostic. Standard header models are
used; missing-header information remains visible. The focused regression
also passes GCC16 and Clang path analysis and has no Cppcheck warning or
error finding.

GCC16 `-fanalyzer` and Clang Static Analyzer 19 analyze all 15 library modules
and the two upstream examples. The two repaired modules are analyzed again
after the series. Existing findings include the stream-size division model,
a dead store, an EOF read in `minigzip`, and a GCC path that enters
`gz_vacate` without its caller's initialized-buffer invariant. These findings
are retained for upstream review; none is suppressed here.

## Installed AArch64 package

The ordinary pkgsrc cross build uses the GCC 16.2.0 application compiler,
the verified E34 fork sysroot from
`6dd57144183678938164b4c2dcfc370cdbde8473`, and the registered
`gcc16-runtime-16.2.0nb2` provider. A normal host dependency build installs
`cross-libtool-base-NetBSD-11.0-aarch64-2.6.2nb1`. The real Linux GNU tar
extracts sources through pkgsrc's supported `EXTRACT_USING=gtar` setting.

The package passes PLIST, permission, PIE, RELRO, RPATH and work-reference
checks. Its metadata records NetBSD 11.0, AArch64 and `gcc-16.2.0`.
Payload ownership is `root:wheel`. Native package tools register it in the
SDK without target script execution; all nine payload entries match the
staged files and link targets. The installed library is `libz.so.1.0.2`,
with SONAME `libz.so.1`. These are the names generated by NetBSD-configured
Libtool 2.6.2. No alias to `libz.so.1.2` is added.

The installed package passes on an EmberBSD AArch64 VM. The upstream
example checks compression, gzip I/O, large streams, synchronization and
dictionaries. The existing writer-seek regression also passes. Upstream
`minigzip` roundtrips the 131072-byte binary payload. SHA256 verifies the
complete decoded data because the minimal VM has no `cmp` command.
Package integrity checks cover all nine entries.

Removal leaves the distinct base provider `/usr/lib/libz.so.1` available.
Reinstallation restores loader selection of `/usr/pkg/lib/libz.so.1` and
passes the example and writer-seek regression again. The loaded package
library matches the SDK SHA256:
`0e2701bf604faa5072381d820ff934c65ec00a2d72e0d0e0ffc3640599ba99cf`.
Target execution covers the shared provider. The Memcheck results above
remain native Linux checks.

## Target source analysis

The target comparison uses all 30 real pkgsrc compiler commands: fifteen
PIC and fifteen static configurations. GCC16 supplies the target macros
and actual fork headers. The Cppcheck platform follows those macros:
LP64, unsigned plain `char`, four-byte `wchar_t` and 16-byte `long double`.

Direct SDK-header import exposes Cppcheck 2.22's unsupported GCC
`__has_builtin` preprocessing operator. The retained complete comparison
therefore uses real GCC16 `-E` output from every original command. No
compiler feature predicate is replaced with a constant. Both source trees
produce the same 163 diagnostic totals: 160 style, two warnings and one
information message. Neither report has an error-severity finding. The two
warnings are the existing size/division model findings in `gzfread` and
`gzfwrite`; they remain visible.

GCC16 `-fanalyzer` and Clang Static Analyzer 19 also check all four gzip
modules with the target compilation settings. Pristine `gzread` and
`gzwrite` fail declaration checks without pkgsrc's `<unistd.h>` adaptation.
The complete series passes every invocation. GCC16 reports no finding;
Clang retains the two division-model findings and one existing dead store.
Native and target raw reports remain separate.

## Shared Chromium compression helper

The package also installs `share/zlib-source/google/compression_utils_portable.{h,cc}`
from Chromium zlib commit `868f187def53b2208f7a0447c069e6ea1ecde7ae`, with
its Chromium BSD license at `share/zlib-source/LICENSE.chromium`. Consumers
compile this one helper with `USE_SYSTEM_ZLIB` and link the common zlib package;
the artifact does not introduce another zlib library or C++ ABI.

## Patched source for freestanding consumers

`devel/zlib-source` installs the common version's patched C sources and headers
under `share/zlib-source/core`, with its license. The source-only package shares
the release, patch revision, distinfo and patch directory with `devel/zlib`.
Each consumer supplies its own freestanding integration and verifies its ABI.
