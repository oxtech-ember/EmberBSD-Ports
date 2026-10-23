# Common SQLite 3.54.1

The common profiles export one SQLite provider as `databases/sqlite3`.
The recipe replaces both pkgsrc 3.53.4 and the former
`local-robotics/sqlite3` 3.54.0 recipe. Consumers use the standard buildlink
path and require 3.54.1 or later. RTABMap no longer requires an exact older
SQLite version. The shared-library ABI remains `libsqlite3.so.0` on ELF.

SQLite released [3.54.1](https://sqlite.org/releaselog/3_54_1.html) on
2026-10-16. It fixes a possible heap-buffer overflow on 32-bit builds and
other problems in 3.54.0. The original archives come from
[SQLite downloads](https://sqlite.org/download.html). Their SHA3-256 values
were checked against that page. The common `sources.tsv` records SHA256;
pkgsrc `distinfo` records BLAKE2s, SHA512 and size. No core C source changes
are carried for this update.

The recipe derives from NetBSD pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. It preserves the upstream platform
settings, optional ICU, readline selection, native build-tool routing and
Darwin configure patch. The existing EmberBSD cross target arguments now
belong to the recipe rather than a second infrastructure patch.

The `readline` option is on by default, except on a Darwin build host.
There, `editline/builtin.mk` does not accept the system library, so the
option would build the editline package. Its autotools chain needs Python,
and Python needs SQLite. Without the option, configure receives
`--disable-readline` and the CLI has no line editing. Target packages keep
the option and the base libedit, so their content does not change.

`features.mk` is the common package and source-probe feature contract.
It retains serialized threads, FTS3/4/5, JSON, RTree, Geopoly, column metadata,
DBSTAT, math, sessions, loadable extensions, statement-vtab and unlock-notify.
The CLI links the selected shared library and explicitly uses the common
zlib provider for SQL archive support. The package preserves the SQLite
public-domain dedication and Autosetup license.

`Makefile.common` also selects `sqlite3-diff`, `sqlite3-docs`, `sqlite3-tcl`
and `lemon`. Their source checksums move with this release. The documentation
PLIST comes from the complete official documentation archive. Tcl's bundled
extension source directory still has the version supplied by Tcl itself;
its `--with-system-sqlite` setting selects this shared provider.

The [SQLite probes](../../../probes/sqlite/README.md) consume this
recipe's flags and patch. Their earlier 3.54.0 results remain historical
evidence. A recipe update does not qualify new target packages, upstream
execution tests, installed consumers, or device behavior by itself.

## Source and host checks

Real native and AArch64 cross metadata checks pass for all five packages.
The native GCC 16.2.0 build on Darwin passes all five installed C and CLI
contract tests. The C consumer also passes with GCC UndefinedBehaviorSanitizer.
Valgrind is not supported on this Darwin host. The separate Tcl extension builds against the selected
shared library. Tcl 9.1 loads the installed module and passes an exact-version
and FTS5 SQL check. The full RTABMap patch series applies to its pinned
archive with pkgsrc `nbpatch -F 0`. These checks do not run target programs.

Check the actual exported family metadata with the SDK host API:

```sh
python3 profiles/common-build-tools/tests/sqlite-metadata.py \
    --sdk-source /absolute/EmberBSD-SDK --bmake /absolute/bmake \
    --makeconf /absolute/mk.conf --pkgsrc /absolute/exported-pkgsrc \
    --distfiles /absolute/distfiles
```

Add `--cross` for a configured cross export. The check validates source
checksums, package identities, the complete documentation PLIST, the private
Tcl source version, shared features, and explicit cross compiler routing.
The Tcl namespace regression rejects a restored global `SQLITE3_VERSION`
assignment from the bundled Tcl extension.
