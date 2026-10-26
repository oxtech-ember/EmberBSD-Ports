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
/absolute/git clone --depth 1 --branch v44.9.3 \
    https://github.com/electron/electron.git /absolute/electron-pristine
/absolute/control-python -B \
    probes/electron/electron44/files/prepare-sources.py \
    --electron-source /absolute/electron-pristine \
    --destination /absolute/NEW_ELECTRON_WORK \
    --git /absolute/git --target-cpu arm64
```

The checkout's actual commit must equal
`c542df1ecbc2c2978e8f53f8c7baf602404d166f`; a matching tag name is insufficient.
The destination parent must exist and the destination must be new and outside
the input checkout. `x64` is the other supported source selection. This selects
dependency source conditions, not the compiler's target ABI.

The helper checks the original Chromium 152.0.7977.167 and Node 24.22.0 DEPS
values and repository URLs without executing DEPS. It applies the complete
recipe-local `patch-*` set through Git with full context and the declared
order. The security roll must produce Node 24.22.1 while retaining the Chromium
version. Adding a recipe patch without adding it to the order is an error.
Already-patched or dirty input, changed pins, missing patches and patch rejects
are errors; none is retried with another version or compiler.

The generated `.gclient` pins Chromium and Node to their immutable commits
through `custom_vars`. Electron is unmanaged at the verified local commit,
with its public upstream remote. The config adds Linux-conditioned shared
sources needed by the BSD overlay and disables downloading a Linux sysroot.
Native host source conditions remain enabled. The eventual target sysroot
comes from the EmberBSD SDK. The helper does not change sandbox or diagnostic
build settings.

The input checkout is preserved. On a preparation error after workspace
creation, partial files remain for diagnosis and `.gclient` is absent. Use a new
destination for another attempt; do not reset a shared work tree. The caller
holds its ordinary source lock throughout preparation and subsequent use.

## Next source stage

This step does not run `gclient sync`, pre-DEPS hooks, upstream patch hooks,
dependency downloads, or GN. The next recipe integration must select an
explicit depot_tools source/revision and its `gclient.py`, control Python and
Git; it must not resolve gclient or build tools from an undeclared ambient
PATH. The upstream source acquisition operation is `gclient sync --nohooks
--noprehooks`, invoked with those declared tools in the prepared workspace.
The flags defer hooks until their native tools and required inputs are bound;
they do not remove the required upstream patch and generator stages.

After synchronization, verify the actual Chromium and Node commits before
applying Electron's upstream patch series, then the ordered Ports BSD series.
The historical `chromium-nb` dry run still has five drifted hunks and fourteen
absent targets. This helper neither applies that incomplete overlay nor claims
that it is ready for the current pins. Those adaptations and the full source
graph remain necessary before the [GN and runtime build](runtime-packaging.md).

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
