# Shared SQLite and installed consumers

The common SQLite target is **3.54.1**, released on 2026-10-16. The
[package recipe](../../pkgsrc/databases/sqlite3) is exported as `databases/sqlite3` and replaces the older pkgsrc
SQLite provider at the same prefix. It introduces no parallel SQLite ABI.
[Provenance](PROVENANCE.md) records the original archive and official checksum.
The [validation boundary](VALIDATION.md) separates completed controls from limits.

The profile retains serialized thread safety, FTS3/4/5, built-in JSON,
RTree, Geopoly, column metadata, DBSTAT and math functions. It installs shared
and static libraries, headers, pkg-config metadata and the CLI. The CLI links
to the selected shared library. The package retains pkgsrc readline selection
and the optional ICU dependency. Session, statement-vtab and unlock-notify
interfaces remain enabled for existing pkgsrc consumers.

## Cross-build with GCC16

Provide a complete EmberBSD AArch64 sysroot from the selected fork and the
common GCC 16.2.0 compiler. Use new output directories:

```sh
sh probes/sqlite/build.sh --cross /absolute/gcc16-prefix /absolute/sysroot \
    /absolute/sqlite-autoconf-3540100.tar.gz /absolute/new-sqlite-build
sh probes/sqlite/check.sh --cross /absolute/gcc16-prefix /absolute/sysroot \
    /absolute/new-sqlite-build/stage/usr/pkg /absolute/new-sqlite-consumer
```

The builder verifies the original archive before extraction. It uses the
canonical recipe features, one job by default, and Autosetup's native C Tcl
bootstrap helper. This configuration has no Python dependency. The generated
AArch64 library and CLI are staged under `NEW_OUTPUT/stage/usr/pkg`.
The consumer helper compiles target code; execute it on EmberBSD separately.

Autosetup requires the canonical configure spelling `aarch64-unknown-netbsd`.
The compiler remains `aarch64--netbsd`; the fork's headers and libraries remain
unchanged. The shared-library SONAME remains `libsqlite3.so.0`.

The dynamic CLI requires make's `LDFLAGS` explicitly. Configure-time LDFLAGS
alone apply to the library and leave the dynamic CLI without its selected
runtime path. The recipe and helper pass both interfaces and check both ELF
runtime paths. No loader environment override is used for acceptance.

## Native controls

For a normal native installation, use the canonical pkgsrc recipe. The helper
can also stage the same source with a native GCC16 compiler for memory checks:

```sh
sh probes/sqlite/build.sh --native /absolute/private-prefix \
    /absolute/sqlite-autoconf-3540100.tar.gz /absolute/new-native-build
mkdir -p /absolute/private-prefix
ruby probes/pcl/cross/import-stage.rb \
    /absolute/new-native-build/stage/absolute/private-prefix /absolute/private-prefix
sh probes/sqlite/check.sh --native /absolute/private-prefix /absolute/new-native-check
```

The stage path appends the selected absolute prefix after `stage`. The shared
[stage importer](../pcl/cross/import-stage.rb) checks all collisions before it
adds files. Existing packages must remain unchanged. This private native
control does not replace installation through pkg_tools on EmberBSD.

The native checker requires GCC 16.2.0, CMake, Ninja and Valgrind. It verifies
actual library resolution for both consumers. Set `RUN_MEMCHECK=0` only when
memory checking is intentionally outside the run; the result records that skip.
The compiler uses GNU C17 for the upstream POSIX shell and library. The local
C consumer uses ISO C99 with explicit POSIX declarations and warnings as errors.

## Contracts and limits

Five installed-consumer CTests cover the complete C database contract, exact
usage failure, existing-database preservation, missing-parent failure, and CLI
behavior. The CLI checks FTS3/4/5, JSON, RTree, math, rollback, integrity, runtime
version and invalid SQL. A native checked run also executes three Memcheck
cases: the C consumer, valid CLI operations and invalid SQL.

The C contract checks prepared parameters, SQL-looking bound text, FTS5 lookup
and absence, malformed FTS/JSON rejection, rollback and WAL snapshot isolation.
It forks with all connections closed, kills only its own uncommitted writer,
and checks the committed data and database integrity after reopen. This proves
process-crash recovery for that scenario. Physical power loss and storage
hardware durability require separate tests.

The GCC16 Linux controls passed all five CTests and all three Memcheck cases
with zero reported errors and no remaining heap allocations. Cross-built
AArch64 library, CLI and installed consumer pass ELF and prefix checks.
Target execution, package lifecycle and RTAB-Map integration are recorded by
the owning RTAB-Map acceptance. No complete upstream SQLite test-suite pass
or physical-board acceptance is claimed.

Run the portable helper guards without compiling another library:

```sh
sh probes/sqlite/tests/input-guards.sh /absolute/gcc16-prefix /absolute/sysroot \
    /absolute/sqlite-autoconf-3540100.tar.gz /absolute/new-guard-results
```
