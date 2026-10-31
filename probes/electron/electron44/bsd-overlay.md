# Ordered BSD overlay source audit

The recipe's `files/audit-bsd-overlay.py` audits the pkgsrc Chromium BSD patches
against Electron's acquired Git graph after its upstream patch stage. It writes
a new source fixture, patch series, per-patch logs and `audit.json`. It does not
modify the source workspace, run hooks, build tools or claim a target runtime.

The baseline is the `www/chromium` recipe in pkgsrc commit
`8b58eb6f903a2788be97e48a5743c25f5432941d`: Chromium 156.0.8078.47,
1,739 ordered `patch-*` files and the `chromium-nb` v154.0 source overlay.
This baseline contributes BSD changes, not a replacement Chromium source tree.
Electron's exact Chromium revision remains the source of record.
The manifest names the public overlay archive and its SHA512 checksum.

```sh
/absolute/control-python -B -I -S electron44/files/audit-bsd-overlay.py \
    --workspace /absolute/electron-source \
    --pkgsrc /absolute/pinned-pkgsrc-checkout \
    --archive /absolute/distfiles/kikadf-chromium-nb-v154.0.tar.gz \
    --destination /absolute/new-bsd-audit \
    --git /absolute/source-tools/git \
    --patch /absolute/source-tools/patch
```

Run from `probes/electron`, after the recipe's Git acquisition and upstream
patch preparation. An installed SDK is unnecessary for this source-only audit.
The explicitly selected Git and patch are control tools. Patch must support
BSD/GNU `-f -N -F 0 -E -p` options; fuzz or three-way fallback is not enabled.
The helper performs no network requests. Obtain the checksum-pinned
`chromium-nb` archive through the pkgsrc distfile source or its public URL.

The helper reads baseline patches directly from their pinned Git tree and
checks their complete pkgsrc distinfo list. It applies a small delta to five
patch files rather than maintaining another full Chromium patch stack.
It reads the relevant committed source blobs from the acquired repositories;
current HEADs must match the acquisition/upstream-patch inventories. Uncommitted
working-tree edits are neither included nor overwritten. Thus the result
checks those committed inputs, not an arbitrary edited workspace.
Only files touched by this patch series and the BSD overlay are materialized.

The complete patch series runs in filename order with zero fuzz. New files
created by patches are distinguished from missing existing source inputs.
A missing ordinary input, changed adaptation preimage, unclassified patch or
patch failure stops the audit without a completion JSON. Failed fixtures and
logs remain available for inspection. Completion JSON is replaced atomically.
No production-tree application command is provided by this audit.

## Adaptations and ownership

The five deltas retain the BSD patch attribution and Electron's behavior:

- File-system access: Electron moved the protected-path list from the source
  file into its header. Add BSD to the guard at its new location.
- Child launch: retain Electron's remapped descriptors, working directory and
  environment handling. Guard the Linux zygote-only `GetZygote` block with
  `USE_ZYGOTE`, matching its API declaration. This is not BSD sandbox acceptance.
- DNS: retain Electron's Mac App Store watcher guard while rebasing the
  existing BSD watcher patch context.
- Fonts: retain Electron's synchronous Fontconfig initialization and extend
  its platform guard to BSD.
- GTK: keep Electron's relocated GdkPixbuf loader and apply the existing BSD
  library-name selection at each loader's current location.

The process-singleton patch affects only dialog code already disabled by
Electron upstream. Its exact source preimage and reason are recorded as
`superseded`; the audit does not re-enable that code.

Six `tools/gn` patches are external host-tool inputs. Electron obtains GN
separately; `pkgsrc/devel/gn` owns its source and compiler selection. The legacy
BSD-host portability changes require review there before any BSD-host claim.
Two `rollup` patches target pkgsrc Chromium's extra Rollup checkout, absent from
Electron's Git graph. Electron DevTools declares Rollup through CIPD. A shared
Ports Rollup provider and consumer binding remain necessary; this audit does
not accept the downloaded native binding as a built Ports tool.
Every external patch stays in the output inventory with its provider and reason.

The full source audit applies 1,632 patches, classifies one as superseded and
retains eight external host-tool patches. This replaces the earlier incomplete
1,622/1,641 independent dry-run result. Remaining Electron-specific GN and
portability patches, pending CIPD/GCS/LFS inputs, native tools and target
compilation are outside this result.

## Regression

```sh
/absolute/control-python -B -I -S tests/electron-bsd-overlay.py \
    --git /absolute/source-tools/git --patch /absolute/source-tools/patch -v
```

The tiny fixtures run real Git and patch. They reproduce the unadapted context
failure, verify the delta, new-file creation, ordered classifications and source
preservation, and reject changed pins/checksums/preimages, undeclared deltas,
missing inputs, fuzz, symlinks, traversal and archive case collisions.
The complete production-source audit is the separate command above. Neither
check compiles Chromium or establishes native/target GN, sandbox or runtime
acceptance.
