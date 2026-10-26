# Shared depot_tools source input

This is the common Ports owner of the depot_tools source pin, ordered patches
and source preparer. It supplies upstream tooling for source acquisition before
an installed native SDK exists. It is not an installable package recipe or a
second build-tool prefix. A future native depot_tools package must consume this
same source definition and patches. Keep a single maintained upstream revision.

The current source is Chromium depot_tools commit
`b86fc981b72ab966f8260f73b4eca600b3b12677` from 2026-10-26. The upstream project
uses a rolling Git history. Obtain this exact commit and prepare it using
control Python with its standard library and an explicit Git executable:

```sh
/absolute/git init /absolute/depot-tools-pristine
/absolute/git -C /absolute/depot-tools-pristine remote add origin \
    https://chromium.googlesource.com/chromium/tools/depot_tools.git
/absolute/git -C /absolute/depot-tools-pristine fetch --depth 1 origin \
    b86fc981b72ab966f8260f73b4eca600b3b12677
/absolute/git -C /absolute/depot-tools-pristine checkout --detach FETCH_HEAD
/absolute/control-python -B scripts/source-inputs/depot-tools/source.py \
    --source /absolute/depot-tools-pristine \
    --destination /absolute/NEW_DEPOT_TOOLS_SOURCE --git /absolute/git
```

The destination parent must exist. The preparer rejects a wrong commit, dirty
input or existing destination, clones without hardlinks, and applies the full
ordered patch set through Git. It preserves the input checkout and uses the
public origin URL. A preparation failure retains partial state for inspection;
it does not reset an existing tree. No source graph, asset, hook or compiler
runs during this operation.

Consumers use `verify_prepared()` from `source.py` before invoking the upstream
CLI. It reconstructs the expected tree from the shared pin and patches using a
temporary Git index, compares the actual index and rejects unstaged or untracked
changes. A raw upstream checkout does not include the shared fix and is rejected.
This is a source-integrity contract, not an SDK or package acceptance format.

## Interrupted Gitlink checkout

The pinned upstream gclient can trust a parent Gitlink in a `git_dependencies =
'SYNC'` graph even when the child has no valid HEAD after an interrupted
checkout. `sync` then returns success, but `revinfo --actual` fails. The shared
patch checks the child's actual HEAD before taking that shortcut. It uses
upstream's existing quarantine/reclone behavior for an invalid checkout.
Valid repositories remain in place; the consumer does not request force or
reset. Preserve `_bad_scm` until any unique input has been recovered.

The [Electron consumer](../../../probes/electron/electron44/source-preparation.md)
invokes gclient's own Git-only filters with hooks disabled and inventories the
pending CIPD/GCS/LFS objects. This patch does not replace gclient, its DEPS parser,
Git LFS, CIPD, or GCS transport. Full asset acquisition still needs its required
upstream tools and their Python/library dependencies through Ports. It is not
established by a Git-only sync.

## Regression

```sh
/absolute/control-python -B scripts/source-inputs/depot-tools/test-source.py \
    --source /absolute/depot-tools-pristine --git /absolute/source-tools/bin/git \
    --source-path /absolute/source-tools/bin
```

Six tests use the actual pinned and prepared gclient. The causal Gitlink fixture
first reproduces upstream's successful sync with an invalid child HEAD and
failed actual inventory. The prepared tool recovers the same workspace, retains
a unique quarantine file, preserves the neighboring Node Git directory and
pack files, and produces the exact actual revision. Other cases check prepared
tree integrity, raw upstream rejection, changed tools, wrong pins and incomplete
patch order. All repositories are local fixtures; no external dependency,
compiler or target program runs.

The upstream source retains its Chromium BSD-style license and attribution.
The carried patch is maintained in Ports and has not been submitted upstream.
