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

Do not add separate source copies or patch subsets for a base library, profile,
board or application. Update the canonical recipe and rebuild affected consumers.
A builtin provider must prove that its installed source identity matches the
recipe. A matching version string alone does not prove that patches are present.
Keep one installed provider on EmberBSD. Reject a stale base and rebuild it;
do not silently add a portable package beside it. Other systems can retain the
recipe's documented portable fallback. The [libedit contract](../pkgsrc/devel/editline/README.md)
provides the current source, builtin and regression interfaces.

## Export the selected closure

Prepare pkgsrc with the existing [Ports exporter](../README.md#package-integration).
Use its complete native/cross MAKECONF and the established GCC16 and base
input receipts. Keep source files and configuration stable during inspection.
`--revision` is caller-declared provenance, not proof of a clean checkout.
The compiler and base arguments hash the supplied receipts. They do not verify
that the installed toolchain or sysroot matches those receipts.

```sh
python3 scripts/export-build-graph.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --pkgsrc /absolute/prepared-pkgsrc \
  --makeconf /absolute/cross.mk.conf \
  --bmake /absolute/host/bin/bmake \
  --pkg-admin /absolute/host/sbin/pkg_admin \
  --target aarch64 --triplet aarch64--netbsd \
  --toolchain-input /absolute/gcc16-receipt.json \
  --base-input /absolute/base-receipt.json \
  --revision ports-commit-id \
  --root security/openssl --root www/curl \
  --output candidate-graph.json
```

The default mode is `cross`. Use `--mode native` and the evaluated host triplet
for a native source graph. `--target` must match evaluated `MACHINE_ARCH`;
the SDK name `amd64` also accepts pkgsrc's `x86_64`. Repeat `--shared-input NAME=FILE` to bind additional
prepared input receipts. Output creation is exclusive. Each metadata subprocess
has a timeout; `--max-nodes` bounds the selected closure.

The exporter asks bmake for expanded dependency variables and loaded makefiles.
It requires native `-dg1` variable inventory output. It queries the listed
`FILESDIR.*` variables with `-V` to resolve shared copied-source trees.
Inventory failures omit the debug dump because it can contain private values.
It passes `PKGNAME_REQD` during dependency evaluation and uses native
`pkg_admin pmatch` to check each selected package. It does not parse Makefiles
or implement a package version solver. All configured dependency kinds are
included by default, including test dependencies and indirect dependencies.

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
receipts for this workflow; do not import bulk `done` entries as success evidence.

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
