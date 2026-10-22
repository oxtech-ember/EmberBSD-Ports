# SQLite validation boundary

The selected recipe is now 3.54.1. The results below apply to 3.54.0 only.
They do not establish acceptance of the new package or rebuilt consumers.
See the [current recipe](../../profiles/common-build-tools/recipes/databases/sqlite3/README.md)
for the migration checks and remaining target work.

## Historical 3.54.0 checks

Source: the official 3.54.0 autoconf archive, verified against the upstream
SHA3-256 and recorded SHA256. SQLite C source has no local patch.
The earlier recipe revision records its source ID and checksums.
The current provenance page describes 3.54.1.

The GCC16.2.0 cross build targets AArch64 EmberBSD with the fork's sysroot.
The library and dynamically linked CLI are AArch64 ELF files, retain the
selected `/usr/pkg/lib` runtime path, and keep SONAME `libsqlite3.so.0`.
All 12 staged files match the canonical recipe PLIST. The installed C consumer
cross-build also resolves the explicitly selected library and headers.
Target execution and pkg_tools installation are separate acceptance gates.

Native Linux controls use GCC16.2.0 and the same SQLite source and features.
Five CTests pass:

- Prepared binding, FTS5, JSON, rollback, WAL snapshot isolation, process crash
  and reopen, database integrity, exact header/runtime source ID.
- Exact usage exit status.
- Existing database preservation.
- Missing-parent failure.
- CLI FTS3/4/5, JSON, RTree, math, rollback, integrity, exact runtime version
  and invalid SQL.

Three Valgrind Memcheck 3.24.0 runs pass: the full C consumer, valid CLI SQL,
and invalid CLI SQL. All report zero errors and zero bytes remaining at exit.
Leak, uninitialized-value and invalid-access checks are enabled without
suppressions. Invalid SQL must return its real status 1; a Memcheck error
would instead return 97 and fail the check.

The CLI test first rejected a system SQLite loaded without the intended
runtime path. The final recipe passes LDFLAGS to make as well as configure.
The repaired CLI loads the selected 3.54.0 library without loader overrides.
Both native and target CLI files were relinked; the library bytes stayed
unchanged. This is a packaging-flag repair, not a SQLite source patch.

The bounded source analysis uses actual AArch64 GCC16 commands, macros and
headers. Cppcheck 2.17.1 and GCC16 `-fanalyzer` complete on the local C consumer:
Cppcheck reports only an informational checker summary; GCC emits no diagnostic.
The complete upstream amalgamation exceeds a 90-second limit in both analyzers.
Cppcheck returns 124 with unfinished XML. GCC returns 124 and reports 321
`-Wanalyzer-too-complex` limits. These are incomplete results, not clean passes.

Pinned upstream and final amalgamation source hashes match. Their actual
target options, macro bytes and 78 header files also match. The final record
reuses the bounded baseline result after proving context equality; it does not
present a copied result as another analyzer run. No diagnostic category is
suppressed and no unsupported source-cleanliness claim is made.

Eight portable helper guards pass without rebuilding SQLite. They check
existing outputs, symlinks, zero worker counts, a corrupt archive before
extraction, relative input and installed-consumer output preservation.

No full upstream SQLite suite, physical board, power-loss durability or
production database workload is claimed by these controls.
