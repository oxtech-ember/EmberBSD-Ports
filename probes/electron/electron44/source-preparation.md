# Prepare the pinned Electron DEPS input

`files/prepare-sources.py` prepares the first source stage of this recipe.
It consumes a clean Electron checkout at the revision in the
[source pins](../README.md#source-pins), copies it without hardlinks into a new
`src/electron` directory, applies the recipe-local patch series in declared
order, and writes an unmanaged `.gclient` solution. It does not require an
installed compiler. Use control Python with its standard library and an
explicit Git executable for this source operation.

For example, obtain the pinned Electron source and prepare an arm64 workspace:

```sh
/absolute/git clone --depth 1 --branch v45.2.1 \
    https://github.com/electron/electron.git /absolute/electron-pristine
/absolute/control-python -B \
    probes/electron/electron44/files/prepare-sources.py \
    --electron-source /absolute/electron-pristine \
    --destination /absolute/NEW_ELECTRON_WORK \
    --git /absolute/git --target-cpu arm64
```

The checkout's actual commit must equal
`f81ca3d4f09f57667238120adacb01239d5ecd89`; a matching tag name is insufficient.
The destination parent must exist and the destination must be new and outside
the input checkout. `x64` is the other supported source selection. This selects
dependency source conditions, not the compiler's target ABI.

The helper checks the original Chromium 156.0.8078.75 and Node 24.22.1 DEPS
values and repository URLs without executing DEPS. It applies the complete
recipe-local `patch-*` set through Git with full context and the declared
order. The security roll must produce Node 24.22.1 while retaining the Chromium
version. Adding a recipe patch without adding it to the order is an error.
Already-patched or dirty input, changed pins, missing patches and patch rejects
are errors; none is retried with another version or compiler.

The generated `.gclient` pins Chromium and Node to their immutable commits
through `custom_vars`. Electron is unmanaged at the verified local commit,
with its public upstream remote. The config adds Linux-conditioned shared
sources needed by the BSD overlay and disables Electron's legacy sysroot
hooks. Native host source conditions remain enabled. Chromium also declares
Linux sysroots as first-class GCS dependencies, independent of that hook
switch. The eventual target sysroot comes from the EmberBSD SDK. The helper
does not change sandbox or diagnostic build settings.

The input checkout is preserved. On a preparation error after workspace
creation, partial files remain for diagnosis and `.gclient` is absent. Use a new
destination for another attempt; do not reset a shared work tree. The caller
holds its ordinary source lock throughout preparation and subsequent use.

## Git-only dependency acquisition

`files/sync-git-sources.py` runs the pinned upstream `gclient.py` with its
supported `--ignore-dep-type=cipd` and `--ignore-dep-type=gcs` filters. It
obtains the selected Git repositories before a compiler SDK is available.
It uses `--nohooks --noprehooks --no-history --no-bootstrap`: no hooks run,
and Git's optional Google Storage bootstrap is also excluded. It does not
replace gclient or its DEPS evaluator with a private downloader.

Prepare depot_tools with its [shared source-input owner](../../../scripts/source-inputs/depot-tools/README.md).
That owner defines the upstream pin and ordered portability patches. Pass its
prepared destination, rather than a raw or privately modified depot_tools
checkout. The Electron helper verifies the exact shared prepared tree.
For a recipe exported outside the Ports checkout, pass `--depot-tools-owner`
with the absolute path to the shared `scripts/source-inputs/depot-tools/source.py`.
Only Git acquisition loads this owner; patch and build-source preparation do
not require a depot_tools checkout.

```sh
/absolute/control-python -B \
    probes/electron/electron44/files/sync-git-sources.py \
    --workspace /absolute/NEW_ELECTRON_WORK --depot-tools /absolute/depot-tools \
    --depot-tools-owner /absolute/EmberBSD-Ports/scripts/source-inputs/depot-tools/source.py \
    --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
    --source-path /absolute/source-tools/bin \
    --jobs 2
```

The supplied source PATH must resolve both the declared Git and Git LFS.
Git LFS is a required upstream acquisition tool (`devel/git-lfs` in Ports).
The helper sets upstream `GIT_LFS_SKIP_SMUDGE=1` so checkout retains LFS
pointers and does not fetch their objects. It does not disable Git's required
LFS filter; the selected Git LFS executable must support `ls-files --json`.
These are explicit control tools for source acquisition, not build-tool
substitutes for the native SDK prefix. The helper invokes
the shared prepared upstream gclient directly with the current control Python
and its standard library; it does not invoke the auto-updating gclient/vpython shell wrapper.
It disables depot_tools telemetry and automatic updates and clears undeclared
GCLIENT_FILE and Git-cache overrides. The caller retains its exclusive source
lock. Failed acquisition retains the Git tree and log for a retry with the same
inputs; it does not request a force-reset or deletion. If an interrupted
checkout has no valid HEAD, the shared gclient can move it under `_bad_scm/`
and fetch that repository again. The shared patch also checks actual HEAD
before accepting a matching parent gitlink in a `SYNC` dependency graph.
Preserve this quarantine until its contents have been inspected. Valid pinned repositories remain in place on retry.

The recipe-owned `source-inputs/` directory contains:

- `acquisition.log`: exact argv and stdout/stderr of the upstream gclient commands.
- `sync.json`: upstream sync output for the filtered graph.
- `declared-dependencies.json`: unfiltered upstream `revinfo` declarations.
- `git-revisions.json`: actual revisions from `revinfo --actual` with the same
  non-Git filters. Each selected Git dependency must match its full pinned
  commit, including Electron, Chromium and embedded Node.
- `pending-inputs.json`: every selected CIPD/GCS declaration omitted from the
  Git inventory, retaining upstream names, URLs and revisions. CIPD platform
  placeholders remain unresolved. Original pinned DEPS files retain GCS
  checksums, sizes and generation metadata.
- `pending-lfs.json`: upstream `git-lfs ls-files --json --include= --exclude= HEAD`
  output for every Git repository containing nonempty LFS object pointers,
  together with the repository URL and commit. It retains file paths, object
  OIDs/types, sizes and observed `checkout`/`downloaded` values. Those two values
  are upstream observations, not content-integrity checks. Empty include/exclude
  arguments prevent local LFS fetch preferences from hiding selected inputs.
  Zero-byte objects have no pending payload and are omitted by upstream.

The inventory does not assert that assets exist, have been downloaded or are
ready for a build. JSON outputs are published only after the three commands
and pin comparison and all LFS scans succeed; a retry removes the previous inventories first.
Use ordinary `revinfo` for declarations: `revinfo --actual` without filters can
query CIPD, and `flatten` can download GCS objects. The helper invokes neither
of those acquisition paths.

The full source graph still requires the pending assets, upstream patches,
BSD adaptations and generators. A full sync without the type filters obtains
CIPD/GCS inputs even with hooks disabled, including upstream tool binaries and
Linux sysroots. LFS payloads need a separate ordinary upstream Git LFS
fetch/checkout stage before their consumers can run; this Git-only helper
retains their pending inventory on every retry. Bind required upstream
acquisition tools and normalize their Python/library dependencies through Ports; select shared Ports build tools
and the EmberBSD sysroot before exposing the full recipe build.

## Upstream patch preparation

After Git synchronization, `files/apply-upstream-patches.py` applies Electron's
own ordered patch series through the pinned upstream `apply_all_patches.py`
CLI. The stage is source-only; pending asset payloads are not downloaded.

```sh
/absolute/control-python -B \
    probes/electron/electron44/files/apply-upstream-patches.py \
    --workspace /absolute/NEW_ELECTRON_WORK \
    --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
    --source-path /absolute/source-tools/bin
```

Before the first patch, the helper requires completed Git acquisition
inventories and verifies all selected targets from Electron's pinned
`patches/config.json`: each must have its own Git repository, the acquired
HEAD and no tracked modifications. It reconstructs the expected Electron tree
from the pinned commit plus the complete ordered Ports recipe series in a
temporary Git index. The real index must match and have no unstaged or untracked
inputs. This includes patch bytes, `.patches` order, the upstream CLI and the
existing Node security roll; the working source is not rewritten. This closes upstream's
warning-only path for an absent repository. A target absent from the selected
DEPS graph is reported as unselected; Mac-only targets need not exist on a
Linux source host. The current config contains 19 targets.

The helper invokes the upstream CLI with one target at a time, preserving its
`.patches` order, Git author metadata and normal patch rejection. It rejects
`ELECTRON_USE_THREE_WAY_MERGE_FOR_PATCHES` rather than selecting a fallback.
It writes `source-inputs/upstream-patches.log` and, only after all selected
series succeed, `upstream-patches.json` with base/patched commits and unselected
targets. This records source state, not build or runtime acceptance. A failure
keeps Git's partial application state and the log; the helper does not reset,
skip a rejected patch or automatically repeat an applied series. Do not run
Git synchronization over this patched tree as an acquisition retry.

The ordered Ports BSD series still needs adaptation and application.
The historical `chromium-nb` dry run still has five drifted hunks and fourteen
absent targets. This helper neither applies that incomplete overlay nor claims
that it is ready for the current pins. Those adaptations and the full source
graph remain necessary before the [GN and runtime build](runtime-packaging.md).

The LFS stage follows upstream [skip-smudge configuration](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-config.adoc)
and the [Git LFS inventory implementation](https://github.com/git-lfs/git-lfs/blob/v3.6.1/commands/command_ls_files.go).
The generated configuration follows the upstream
[Electron source layout](https://www.electronjs.org/docs/latest/development/build-instructions-gn#manual-setup-advanced)
and depot_tools [gclient configuration](https://chromium.googlesource.com/chromium/tools/depot_tools/+/refs/heads/main/gclient.py).

## Regression checks

```sh
/absolute/control-python -B probes/electron/tests/electron-source-prepare.py \
    --git /absolute/git --electron-source /absolute/electron-pristine
```

Seventeen tests exercise real local Git repositories, successful preparation,
source preservation, version and URL mismatches, dirty and already-patched
inputs, duplicate and unlisted patches, patch order, patch rejection and
destination reuse. The optional `--electron-source` case additionally applies
the complete production recipe-local patch set to the real pinned checkout.
Fixtures are removed after the tests. These checks establish DEPS input
preparation only; they run no full dependency sync, compiler or target runtime.

The Git-only acquisition regression uses the real shared prepared upstream gclient and
small local Git repositories. It checks nested deferred assets, exact Git
commits, retry, invalid inputs, and hook refusal. Fourteen tests also check
an actual LFS pointer with spaces in its path, include/exclude independence,
missing Git LFS refusal, incomplete-inventory rejection, and preservation of
an interrupted checkout in gclient's quarantine while reusing the Node clone.
A no-skip control verifies that the unavailable local LFS object causes an
error; the normal Git-only stage preserves its pointer. A separate upstream
`runhooks` control proves that the fixture hook would execute when requested.
No external repository or asset is downloaded by this test:

```sh
/absolute/control-python -B probes/electron/tests/electron-git-sources.py \
    --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
    --source-path /absolute/source-tools/bin \
    --depot-tools /absolute/depot-tools
```

The upstream patch guard regression copies the actual patch CLI and its two
library modules from a clean pinned Electron checkout. Twelve tests apply ordered
mail patches to tiny local repositories, preserve author metadata, reject
missing selected repositories before any patch, retain unselected host targets,
and reject changed pins, dirty targets, incomplete acquisition, changed upstream
code/config, edited patch bytes, changed staged patch order, duplicate
application and three-way fallback. A production-source case verifies that the
real Node security roll matches the expected tree without altering its index. Reversing a dependent
patch pair is a causal rejection test and retains Git's failed application state.

```sh
/absolute/control-python -B probes/electron/tests/electron-upstream-patches.py \
    --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
    --source-path /absolute/source-tools/bin \
    --electron-source /absolute/electron-pristine
```

## Ordered build sources

[prepare-build-sources.py](files/prepare-build-sources.py) consumes the pinned
BSD overlay and [source-series.json](files/source-series.json). This is the
single full application order for the additional NetBSD and GN/C++ patches.
It reads committed source preimages from the existing Git graph, prepares a
separate touched-file tree and uses strict Git patch matching for the ordered
Ports layer. It never runs gclient, hooks, configure or a compiler.

```sh
/absolute/control-python -B -I -S \
  probes/electron/electron44/files/prepare-build-sources.py \
  --workspace /absolute/electron-workspace \
  --pkgsrc /absolute/pinned-pkgsrc-checkout \
  --archive /absolute/distfiles/kikadf-chromium-nb-v154.0.tar.gz \
  --patch-root /absolute/Ports/probes/electron/patches \
  --git /absolute/git --patch /absolute/gpatch \
  --destination /absolute/new-source-preparation
```

Add `--apply` to materialize the result while holding the normal exclusive
workspace ownership. Every target is checked before the first write. Only its
exact committed preimage or exact prepared result is accepted, so the operation
can resume after an interrupted write without applying a patch twice. It rejects
unrelated local changes and symlink paths. Completion metadata is replaced
atomically in `source-inputs/ports-build-sources.json`. This describes prepared
source bytes and is not compiler, package or runtime acceptance.

The additional layer replaces the former combined E12 patch. Duplicate BSD
files and binary host artifacts are removed; host tools come from common Ports.
The obsolete Apple Clang diagnostic workarounds and fabricated zlib metadata are
not applied. The selected SDK supplies native tools and target package metadata.
The old Clang21 resource rewrite is superseded explicitly in the series. A
context-only update to the recursive `std::function` clone patch permits strict
Git matching without changing its C++ behavior.

The full pinned-source check applies 1,632 BSD patches and 97 ordered Ports
patches. Eight tiny real Git/patch regressions check order, pin mismatch,
all-before-write refusal, symlinks, changed prepared bytes and repeat application:

```sh
/absolute/control-python -B -I -S probes/electron/tests/electron-build-sources.py \
  --git /absolute/git --patch /absolute/gpatch
```

Remaining dependency assets and the ordinary GN/Ninja recipe binding are
separate work. Source preparation alone does not establish a complete build.

An ordered-series extension can also materialize over an earlier exact prefix.
Preparation reconstructs and hashes each affected file immediately before each
ordered Ports patch. Materialization accepts those reconstructed bytes as well
as the committed preimage and final bytes. It does not trust arbitrary live
changes or an old completion file to authorize an overwrite. A changed earlier
patch whose old result is no longer reconstructed is refused.
