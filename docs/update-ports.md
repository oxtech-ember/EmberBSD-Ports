# Plan a Ports update with Codex

The coding agent evaluates a prepared pkgsrc tree, compares immutable locks,
and runs the existing package producers. It inspects failures and patches the
responsible recipe or consumer. These Python standard-library tools do not
select new releases, download sources, run producers, or modify a device.

Use an explicit [EmberBSD SDK](https://github.com/oxtech-ember/EmberBSD-SDK)
source checkout with `PORTS_PLAN_API = 1`. The first compatible SDK revision is
`3d27627020c9070415d5232c7f72130c3d2ba90f`. The SDK owns graph validation,
input keys, plans, evidence receipts, hashing, and JSON file writes.

## Shared base dependencies

Keep one canonical Ports recipe for each third-party library shared with the OS
base. The recipe owns the source pin, archive hashes and complete patch set.
Base build rules consume those prepared sources and retain the native OS ABI,
header installation and build integration. SDK tools own host preparation.

Update the canonical recipe and its complete patch set for base libraries,
profiles, boards and applications. Rebuild affected consumers from that shared source.
A builtin provider must prove that its installed source identity matches the
recipe. A matching version string alone does not prove that patches are present.
Keep one installed provider on EmberBSD. Reject a stale base and rebuild it
from the canonical recipe before resuming its consumers. Other systems can retain the
recipe's documented portable fallback. The [libedit contract](../pkgsrc/devel/editline/README.md)
provides the current source, builtin and regression interfaces.

## Export the selected closure

Prepare pkgsrc with the existing [Ports exporter](../README.md#package-integration).
Use its complete native/cross MAKECONF and files identifying the selected
toolchain and base inputs. Clang/LLVM is the default SDK toolchain; select GCC
explicitly when the platform profile requires it. Keep source files and
configuration stable during inspection.
`--revision` is caller-declared provenance, not proof of a clean checkout.
The compiler and base arguments hash the supplied files. They do not verify
that the installed toolchain or sysroot matches those files.

```sh
python3 scripts/export-build-graph.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --pkgsrc /absolute/prepared-pkgsrc \
  --makeconf /absolute/cross.mk.conf \
  --bmake /absolute/host/bin/bmake \
  --pkg-admin /absolute/host/sbin/pkg_admin \
  --target aarch64 --triplet aarch64--netbsd \
  --toolchain-input /absolute/selected-toolchain-input.json \
  --base-input /absolute/selected-base-input.json \
  --revision ports-commit-id \
  --root security/openssl --root www/curl \
  --output candidate-graph.json
```

The default mode is `cross`. Use `--mode native` and the evaluated host triplet
for a native source graph. `--target` must match evaluated `MACHINE_ARCH`;
the SDK name `amd64` also accepts pkgsrc's `x86_64`. Repeat `--shared-input NAME=FILE` to bind additional
prepared input receipts. Output creation is exclusive. Each metadata subprocess
has a timeout; `--max-nodes` bounds the selected closure.
Use `--jobs N` to bound concurrent bmake metadata queries; it defaults to 1
and does not schedule package builds or change graph contents.

Pass an early MAKECONF policy input as a repeatable `--make-variable NAME=VALUE`
option, for example `--make-variable EMBERBSD_DARWIN_BOOTSTRAP=yes`. The
assignment is passed to every bmake metadata query, including recursive and
pattern checks, and is recorded in graph provenance and shared input hashes.
This accepts scalar assignments only; it does not accept make targets or flags.
`MAKECONF`, `USE_CROSS_COMPILE`, and target-routing variables remain controlled
by the exporter.

Host-only metadata uses repeatable `--native-make-variable NAME=VALUE`. It has
the same scalar, reserved-name, and duplicate checks, and a name cannot also be
a global `--make-variable`. The assignment is added only to native role queries
(`USE_CROSS_COMPILE=no`), including tool dependencies and the native packages
those tools depend on. Target queries do not receive it. It is absent from the
global `make-variables` digest and from target node hashes. Provenance records
it as `native make variables`, and `shared_inputs` records
`native-make-variables` only when at least one assignment is present.

On Darwin, native `lang/compiler-rt` rejects a metadata query unless
`OSX_SDK_PATH` and `EMBERBSD_DARWIN_SDK_VERSION` are both set. A selected host
prefix `mk.conf` can already provide `OSX_SDK_PATH`. Pass the SDK version with
`--native-make-variable`; do not pass it with global `--make-variable`, because
that stamps Darwin SDK metadata onto NetBSD target queries. The compiler-rt
guard does not read `MACOSX_DEPLOYMENT_TARGET`, and the graph does not
synthesize one. Read `sdk_version` from the selected SDK with the SDK reader
`scripts/darwin-sdk.py --macos-sdk <absolute SDK> --xcode-version-plist
<absolute Xcode Contents/version.plist>`. Do not derive the version from the
SDK directory name, the host ABI, or `xcrun`. The frozen recipe tree,
MAKECONF, and `--revision` stay the sources that were built. A newer exporter
may query that frozen tree; its own file digest is the `exporter` shared input.

`--host-current` checks installed host tools in the package database selected by
that same frozen MAKECONF. It is explicit: without the flag the closure is
unchanged. The exporter runs four `bmake -C pkgtools/pkg_install show-var`
queries, each with `MAKECONF=` set to the selected file. The first reads
`EMBERBSD_NATIVE_TOOLSET_VERIFIED` and does not pass `USE_CROSS_COMPILE`. The
next two pass that verified value and `USE_CROSS_COMPILE=no` and read
`PKG_INFO` and `_HOST_PKG_DBDIR`. The fourth passes the verified value without
`USE_CROSS_COMPILE=no` and reads the target `_PKG_DBDIR`. This is the same
selection `scripts/cross-bulk.sh` uses when `MAKECONF` is already exported.

`PKG_INFO` must be an absolute executable with one absolute `-K` directory.
That directory must resolve to the host database and must not resolve to the
target database. For each host node the exporter reads bmake `PKGBASE` and the
node's `PKGNAME`. When `PKGNAME` matches `PKGBASE-[0-9]*`, it runs
`pkg_info -e 'PKGBASE>=suffix'`; otherwise it runs `pkg_info -e PKGBASE`. Exit
0 means the installed package is current, exit 1 means it is not, and any
other status fails the export. A current host node keeps only its `DEPENDS`
edges. Build, tool, bootstrap, and indirect dependencies are not queried. In
the build phase its `TEST_DEPENDS` remain in the test-requirements inventory
and are not queried or turned into edges. Target nodes are not asked.

The mode records `host-pkg-info-argv`, `host-pkg-info-binary`, and the sorted
`pkg_info -a -Q PKGNAME` listing as `host-pkg-names`. The listing is hashed
again after the walk and the export fails, without writing a graph, if the
database changed. `pkg_info -e` is the current decision. `PKGBASE` is not
added to the hashed metadata, so node input hashes stay independent of it.
Provenance includes `host current package database`.

The exporter asks bmake for expanded dependency variables and loaded makefiles.
It requires native `-dg1` variable inventory output. It queries the listed
`FILESDIR.*` variables with `-V` to resolve shared copied-source trees.
Inventory failures omit the debug dump because it can contain private values.
It passes `PKGNAME_REQD` during dependency evaluation and uses native
`pkg_admin pmatch` to check each selected package. It does not parse Makefiles
or implement a package version solver. All configured dependency kinds are
included by default, including test dependencies and indirect dependencies.

For cycle diagnosis, `--diagnostic-graph PATH` writes the evaluated raw graph
only when SDK graph locking fails. Keep this separate scratch output distinct
from the accepted graph and test-requirements paths.

pkgsrc installs `TEST_DEPENDS` through its separate `test-depends` stage.
This can create a cycle if all stages share one graph: Perl builds with GNU
make, while GNU make tests with Perl. For a build plan, explicitly select
`--dependency-phase build --test-requirements-output pending-tests.json`.
Build, bootstrap, tool, runtime and indirect dependencies remain in the graph.
Real build cycles still fail. The phase is part of provenance and shared input
keys, so a build-phase receipt cannot qualify an all-phase plan.

The mandatory `ports-test-requirements-v1` inventory records the graph file's
SHA256 and each pending test dependency's owner, host/target role, package path
and native pattern. It is an inventory, not a resolved test closure or a test
result. Test-only package constraints are not evaluated by the build graph.
Export their separate build closures in the recorded roles with the same
configuration. Then run native pkgsrc `test-depends` to validate and install
those dependencies before the selected upstream tests. Cross tests still need
their documented target runner. Keep the inventory pending until those tests
have real evidence. A successful build does not accept them.

For binary distribution, `--dependency-phase runtime` visits only `DEPENDS`
and `INDIRECT_DEPENDS`. It does not query build, bootstrap, tool or test providers
and does not require a pending-test inventory. The phase is part of graph input
identity. Use it for already produced packages, not as a source-build plan.
The SDK [binary catalog producer](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/binary-catalog.md)
consumes this graph, checks native package dependencies with pkg_tools, signs
packages and creates pkg_summary from the signed bytes. Clients receive the
resolved catalog rather than running bmake or maintaining another resolver.

Both output paths must be new and distinct. Publication uses two exclusive
writes, not a multi-file transaction. A failed second write can leave an orphan
inventory; use it only with the graph whose hash it records.

Cross routing follows `mk/pkgformat/pkg/depends.mk`: bootstrap and tool edges
select native packages and receive the parent's `CROSSTARGETSETTINGS`. Build,
runtime, and test edges retain the parent's cross mode. The test routing follows
the installer implementation, which differs from the comment in
`mk/depends/bsd.depends.mk`. Recursive package environment assignments are
retained, with PATH restored to `_PATH_ORIG` as in the native installer.

IDs distinguish `target:category/package` and `host:category/package`.
An explicit target context adds a deterministic `@hash` suffix to a host ID.
This preserves host generator variants. It does not provide separate installation
prefixes or make those variants safe to install together. Existing producers
remain responsible for output paths and package installation conflicts.

The input hash covers effective query environments, target settings, required
package patterns, evaluated metadata, loaded makefiles, package files,
`PATCHDIR`, `FILESDIR`, additional `FILESDIR.*` trees, `DISTINFO_FILE`,
`PLIST_SRC`, and the package's subtree
under `LOCALPATCHES`. A copied-source change updates its consumers' input hashes
without adding package dependency edges. External paths stay out of graph output. Configuration,
bmake, pkg_admin, the exporter, and its restricted environment are shared inputs.
Private values can affect hashes without being printed in the graph.

Missing packages, unmatched patterns, conflicting contexts, cycles, and pkgsrc
skip/failure reasons stop export. An existing GCC16 provider placeholder can
report `Import the repaired target GCC16 package and metadata before building
consumers`. Complete that documented preparation before exporting its closure.
The exporter does not bypass this prerequisite or import a compiler itself.

## Compare, build, and record

Export and lock the baseline before changing recipes. Then export and lock the
candidate. Use new output names for each immutable snapshot.

```sh
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py lock baseline-graph.json --output baseline-lock.json
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py lock candidate-graph.json --output candidate-lock.json
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py plan baseline-lock.json candidate-lock.json --output plan.json
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py status plan.json
```

Codex runs the existing producers for ready nodes and checks their real exit
status, logs, packages, and required regressions. The plan's waves express
ordering; they do not allocate build resources or grant installation permission.

The separate `scripts/cross-bulk.sh` helper has a different resume contract.
Its `done` records compare package names and output hashes, without binding build
inputs. Those records cannot qualify reuse under an update plan. Use the SDK
receipts as success evidence for this workflow. Keep bulk `done` entries scoped
to the separate cross-bulk resume contract.
For a fresh control build, use cross-bulk directly; the graph exporter and SDK
plan/receipt workflow are optional incremental-update tooling.

When running cross-bulk with a prefix-only `PATH`, prepare the common native
command aliases first and invoke the helper with the selected prefix shell. The
aliases provide command names such as `awk` and `sh` without using host tools
outside the selected prefix:

```sh
"$HOST_PREFIX/bin/python3.15" -B -E -S \
  "$PORTS/profiles/common-build-tools/cross/prepare-native-tools.py" \
  --sdk-source "$SDK_SOURCE" aliases --host-prefix "$HOST_PREFIX" \
  --output "$NATIVE_ALIASES"
PATH="$NATIVE_ALIASES:$HOST_PREFIX/bin:$HOST_PREFIX/gnu/bin" \
  BMAKE="$HOST_PREFIX/bin/bmake" MAKECONF="$MAKECONF" PKGSRCDIR="$PKGSRCDIR" \
  "$NATIVE_ALIASES/sh" "$PORTS/scripts/cross-bulk.sh" order "$PKGPATH_LIST" "$STATE"
```

Use the same environment and state for the subsequent `fetch` and `build`
phases.

The `build` phase drains independent runnable packages after a package fails.
Exit 0 means the pass completed without failed or blocked packages; exit 1
means at least one package failed or was blocked. Inspect `STATE/failed`,
`STATE/blocked`, and `STATE/skipped` to resume only affected work. Usage,
invalid mode, and explicit CLI validation errors exit 2; SIGTERM exits 143
after running packages finish.

```sh
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py record plan.json target:www/curl \
  --outcome failure --log /absolute/logs/curl.log --output curl-failed.json
python3 /absolute/EmberBSD-SDK/scripts/ports-plan.py status plan.json --receipt curl-failed.json
```

For successful work, use `--outcome success` and at least one `--artifact FILE`.
A failed producer never justifies a success receipt for an older artifact.
A compatibility patch requires a fresh export, lock, and plan. Follow the
[SDK evidence and resume contract](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/ports-plan.md#validate-results-and-resume)
for unchanged dependencies and reusable artifacts.
Reuse follows the common [input key rule](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/input-keys.md). A matching key means reuse
without rereading, rehashing or re-archiving sources, stages or outputs. Use the recorded Git hash or input key to identify those unchanged inputs.

## Checks and limits

The libzip consumer `textproc/ebook-tools` uses CMake on the build host.
Its common-profile recipe removes a redundant target CMake buildlink.
The source only links libzip and libxml2; `devel/cmake/build.mk` still owns
the native generator. Check this boundary against an unchanged pkgsrc export:

```sh
python3 profiles/common-build-tools/tests/ebook-tools-cmake.py \
  --pkgsrc /absolute/baseline-pkgsrc --makeconf /absolute/cross.mk.conf \
  --bmake /absolute/host/bin/bmake --work /absolute/new-check-directory
```

This check evaluates real dependencies before and after the recipe patch.
It does not compile ebook-tools or establish target execution.

```sh
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
  python3 scripts/tests/test_export_build_graph.py
```

Subprocess regressions cover native/cross roles, host context variants, native
constraint failures, shared includes, package and local patches, input pins,
cycles, and bounded traversal. A real native bmake/pkg_admin smoke exports the
four-package digest, mktools, cwrappers, and libnbcompat closure on Darwin.
Real cross metadata confirms the target digest and native tool transitions;
the inspected prepared closure stops at the GCC16 provider prerequisite above.
A complete real cross graph and package build are not yet accepted by these checks.

The tool supports the selected configuration and its native package path choices.
It does not enumerate pbulk multi-version combinations, search alternate providers,
or model source-generated host tools absent from pkgsrc dependency metadata.
Such tools need explicit producer input receipts. Metadata evaluation can run
pkgsrc parse-time probes; use a trusted prepared tree. No build target is invoked.

## Refresh configuration metadata

When a retained package has the same identity but its resolved dependency
metadata changes, ordinary bulk builds stop that job and preserve its WRKDIR,
objects, phase cookies and previous dependency metadata. The worker log records
the old/new dependency diff before temporary query outputs are removed.
Dependency names and roles alone do not establish object compatibility. For a known compatible
tool, documentation or packaging change, use the existing scoped `package` /
`package-install` or reconfigure path described below. Incompatible ABI or
compiler changes require rebuilding the affected objects; the dependency
check does not silently accept them or clean the whole stage.

Selecting a package for a source build does not establish that its retained
objects are incompatible. A change of `nbN` alone preserves the work directory
and stops for the scoped recovery described here; it does not authorize a clean.

The explicit stage-local `package` and `package-install` commands also compare
retained dependency metadata with the current resolution. A change refreshes
only dependency and package metadata through `depends-clean` and `_package-clean`,
even when the package name is unchanged. Build/install cookies and compiled
objects remain intact, and the package records current `@blddep` names. A failed
dependency query stops before cleanup or packaging and preserves the old stage.
Choosing this scoped recovery path does not establish ABI compatibility.

When a selected package's provider configuration changes, `invalidate-makevars`
removes that work directory's cached phase variables, without removing source,
objects or phase cookies. It does not itself reconfigure or rebuild. For a
provider changing from builtin to pkgsrc, `refresh-empty-buildlink-<provider>`
rebuilds its links only if the previous buildlink cookie is empty; it refuses
a nonempty or invalid cookie. Run these explicit targets without another
writer in the same work directory. Then use `bmake reconfigure` followed by
`bmake build`: reconfigure runs the normal barrier and preserves source and
compatible objects while resetting the build phase. Packages with `NO_CONFIGURE`
keep their existing configure behavior. Meson setup reconfigures an existing
valid build directory in place.

For generated documentation or assets, rerun the generator or its incremental
build target, retaining the compiled inputs. Ninja's `-t clean <target>`
recursively removes outputs of that target's dependencies: cleaning a
documentation target can also delete library objects and linked binaries.
When an output must be regenerated explicitly, remove only the identified
generated output, not its dependency closure.

For a new patch set with changed recipe configuration, use `patch-refresh`
with `CROSS_BULK_PATCH_REFRESH_RECONFIGURE=yes` and
`CROSS_BULK_PATCH_REFRESH_PREVIOUS_RECIPE=/absolute/previous/recipe`.
This explicit mode accepts new local includes and configure hooks. It verifies
the source preimages and invalidates configuration while retaining
objects. It rejects changes to the source archive, toolchain, ABI and compiler
flags. It clears the accepted old dependency/package metadata and advances
existing compatible phase identities to the current package revision, without
creating a configure/build completion cookie. Identity-only updates retain
phase timestamps so make does not reapply already verified patches.
Then resume the ordinary SDK install/bulk build, or `package` / `package-install`,
to run normal configuration and incremental compilation. Without this selector, new includes remain
restricted to revision metadata with unchanged build inputs and commands.

An unfinished first build has no installed package metadata. With the explicit
previous-recipe selector, refresh replays the applied patches listed in the
existing `.patch_done` cookie, including an empty cookie, against the verified
archive. The cookie must be an ordered subset of the previous recipe's complete
patch inventory. Both recipes' archive checksums and complete patch inventories
are validated. The replay extracts the full endpoint set for both patch
inventories, including header spellings and `.orig` backup paths, plus inputs
named by `SUBST_FILES.*` and `REPLACE_FILES.*`. Unrelated archive members are
not extracted; a root-level `SUBST` or interpreter-replacement glob requires
full archive scope. All old/current patch targets, including unchanged targets
and expected absent files, must match the old replay before any live source
write. Then refresh applies the complete current series, preserving unchanged
source and object timestamps. No package database entry is created. Without a
previous recipe, ordinary refresh still requires valid installed provenance.

For already applied substitutions, set
`CROSS_BULK_PATCH_REFRESH_EXISTING_SUBST='fix-paths wx-rpath'` with the previous
recipe selector. The helper accepts repeated `--refresh-subst CLASS` arguments.
Selected classes replay in pkgsrc's lexical class order, regardless of argument
order, and retain their individual cookies. Multiple selected classes must share
one supported stage; mixed stages are refused. Unselected substitutions retain
their existing source-intersection checks.

Candidate replay follows pkgsrc stage order: `SUBST_STAGE=pre-configure` runs
before the `replace-interpreter` configure hook; for `do-configure-pre-hook`,
bmake runs the already-declared interpreter prerequisite before a later SUBST
prerequisite. The transaction journal stores the selected interpreter replay
state, so an ordinary retry can reproduce those rewrites after `configure-clean`
removes the configure cookie.
For GNU-configured packages, the same completed-configure evidence also replays
only `configure-scripts-override` and `configure-scripts-osdep`, before interpreter
replacement. Their selected framework definitions and script selectors must agree
between recipes. Other configure prerequisites, including autoreconf, are not run.
The common override recognizes the exact existing two-line `--recheck` guard and
leaves an unchanged script's bytes, mode and timestamp intact on repeat configure.
Unrelated live edits still fail the transaction's exact preimage comparison.

For an explicitly failed source stage whose saved `.patch_done` cookie is an
ordered subset of the selected previous recipe's complete patch inventory, use
`CROSS_BULK_PATCH_REFRESH_RECOVER_APPLIED_PATCHES=yes` together with the
previous-recipe selector. That recipe describes the prepared source, which may
be newer than the installed package when configuration or compilation failed.
This recovery replays exactly the cookie's applied patches as the live preimage,
verifies both recipes' complete patch checksums and archive checksums, and
applies the complete current patch set transactionally. Every
changed live file must match that replay before any write; an unrelated or
modified preimage is refused. Ordinary refresh keeps its full previous-recipe
replay and stale-cookie checks.

Ordinary native and target builds use the same configuration preservation path
as scoped `package` and `package-install`, after the existing workdir identity
and dependency checks. Changed `USE_TOOLS` entries refresh their wrappers before
configure; this also updates aliases such as `make` when a recipe adds `gmake`.
Removed tools are compared with their previous factory output before removal;
aliases retained by a current tool are updated, and interrupted changes can resume.
Unchanged generated configure inputs retain their timestamps. This path adds
newly missing pkgsrc buildlink providers. The existing factory
creates their links under the stage lock. Existing provider cookies and compiled
objects remain intact. Interrupted additions can be retried. This refresh path
does not support new or changed libtool `.la` outputs.
