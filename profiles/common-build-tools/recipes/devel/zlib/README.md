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

The latter two changes are AI-assisted EmberBSD fixes. They have not been
submitted upstream. The first patch preserves the existing pkgsrc adaptation.
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
These results establish native package behavior, not target acceptance.

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

AArch64 GCC16 syntax checks of all four gzip modules pass with the verified
EmberBSD fork headers. The kernel-mode frontend requires an explicit target
header search path for that check. This does not prove target linkage,
packaging, installed consumers, memory behavior or VM execution. Those
checks require the complete application toolchain and installed package.
