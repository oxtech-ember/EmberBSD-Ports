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
Revision nb1 adds `SQLITE_ENABLE_RBU` for the common Node24 SQLite capability
contract. RBU is already part of the upstream amalgamation; no second SQLite
provider or core-source patch is introduced. The package dependency minimum
includes nb1 so future consumers receive that capability. Existing exported
C symbols and the shared-library ABI are retained; compatible installed
consumers do not need rebuilding solely for this additive feature.
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

The Darwin post-install ID command uses `EMBERBSD_DARWIN_INSTALL_NAME_TOOL`
when the native SDK selects it. This is the same explicit executable variable
used by the common CMake mapping. An undefined variable keeps the ordinary
`install_name_tool` command. The path is shell-quoted as one argument. A literal empty quote keeps an
explicitly empty value from becoming a bmake command-prefix flag.
The Tcl extension and coreutils post-install command use the same mapping.
The actual ID update and normal package checks remain required.

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

`tests/rbu.py` verifies the release archive and canonical patch, configures the
shared feature contract, and compiles two native libraries differing only in
RBU. The baseline reports no capability and cannot link the RBU API; the
candidate performs insert/update/delete, suspend/resume and malformed-input
rejection. Exported symbols are additive. The existing C consumer is linked
once against the baseline and runs unchanged with each library, covering SQL,
FTS/JSON, transactions, readers and crash/reopen behavior.

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S pkgsrc/databases/sqlite3/tests/rbu.py \
  --sdk-source "$SDK_SOURCE" --host-prefix "$HOST_PREFIX" \
  --archive "$DISTDIR/sqlite-autoconf-3540100.tar.gz" --work "$NEW_WORK"
```

On Darwin, pass the selected host ABI SDK using `--abi-flag=-isysroot` and
`--abi-flag="$MACOS_SDK"`, with any explicit deployment flag. Add `--sanitize`
to instrument the libraries and consumers with ASan/UBSan in a new output.
These are native source/API checks, without package installation, target
execution or the complete Node test suite.

Darwin arm64 Clang 23 controls passed in ordinary and ASan/UBSan builds. The
new C regression also passes Cppcheck and Clang Static Analyzer without
diagnostics. Valgrind is unavailable on this host. Actual bmake metadata
selects nb1 and forwards its capability minimum to Node24, Python315 and the
Tcl extension; package rebuild/installation and Node-suite acceptance remain
separate from these checks.
