# Cocoa context ownership during fenced scanout

The local [patch](cocoa-context.patch) preserves the caller's current GL
context while Cocoa updates its display texture. It fixes a real failure
encountered by the installed Mesa26/wlroots DRM consumer in an isolated
VirGL trial guest on the paired QEMU/ANGLE Metal host. It does not change
renderer fence validation or guest error handling.

## Observed cause

The first offscreen guest VirGL draw passed, but the first DRM modeset failed.
QEMU's existing trace events identified this exact sequence:

```text
virtio_gpu_cmd_set_scanout id 0, res 0x0, w 1280, h 800, x 0, y 0
virtio_gpu_fence_ctrl fence 0x16, type 0x103
Failed to create fence sync object
```

The guest's normal `mode_set_nofb` sends a fenced scanout command with no
resource. QEMU replaces the disabled output with a placeholder surface. Its
synchronous Cocoa switch/update callbacks temporarily select the display GL
context, then unconditionally clear the current context. The next operation
is creation of the command fence. `glFenceSync` returns null without a current
context; the renderer returns an error and the paired lifecycle path requests
a reset. The nonzero-resource scanout branch already restores renderer
context zero after resizing; the empty-resource branch exposed the lost state.
An offscreen render-node consumer does not exercise this initial modeset.

The initial guest also panicked while freeing a reset virtqueue. That is a
separate OS error path; this patch neither repairs it nor treats a successful
fence as a substitute for safe reset handling.

## Change and source boundary

`with_gl_view_ctx` now saves EGL display, context, draw surface and read
surface, then restores the exact tuple after its callback. When no context
was current, it unbinds using QEMU's valid EGL display: `EGL_NO_DISPLAY` is not
a valid display argument to `eglMakeCurrent`. Nested callbacks restore their
caller's state too. The CGL branch of the same helper preserves its previous
context, including null, rather than always clearing it.

Failure to bind or restore emits `error_report` and exits with failure. The
helper's void interface cannot propagate that failure to the renderer command
dispatcher. Continuing could create a successful fence in the wrong context.
This terminal failure is deliberate; it is not a retry or software fallback.
The acceptance environment uses an isolated snapshot image, never an active
user VM disk.

The full QEMU source remains the archive and complete UTM overlay pinned in
[sources.tsv](sources.tsv) and [create-sources.tsv](../create-sources.tsv).
The local patch applies after the accepted paired whole-file stages. The
[preparer](prepare.sh) checks the exact Cocoa baseline, patch and resulting
file SHA256 and rejects fuzz, offsets, duplicate or failed application.
All other QEMU and renderer source remains unchanged by this repair.

Cocoa's original Mike Kronenberg copyright and MIT notice are retained.
The test also extracts the original QEMU VirtIO GPU function, retaining its
Red Hat authorship and GPL-2.0-or-later notice and copying QEMU's `COPYING`
into each test work directory. The patch and regression are AI-assisted
EmberBSD work and have not been submitted or accepted upstream.

## Focused regression

```sh
ruby test-cocoa-context.rb /absolute/accepted-qemu/src /absolute/new-check
```

The test extracts the actual scanout function and Cocoa helper/switch/update
bodies. Only GL operations, resource metadata and embedding boundaries are
modeled. The original code fails both empty-resource scanout cases at the
next fence boundary; the nonzero-resource control passes. The patched source
passes both cases, exact EGL tuple preservation, the no-context case, nested
callbacks, CGL ownership and fatal bind/restore failure checks. Controlled
wrong-read-surface and lost-context mutations fail their intended assertions.

All 36 cases run both normally and with ASan/UBSan included in that count.
Four additional cases execute the actual preparation guard block against
unchanged inputs and changed source, patch or expected result. Exact patch
application and duplicate refusal are checked separately. These software
contracts do not create a real EGL context, fence or presentation.

The isolated incremental QEMU build preserves the accepted executable and
uses a separate APFS clone. It verifies the full original source receipt,
applies the actual preparation guard block, checks the resulting full source
receipt, recompiles only the real Cocoa translation unit, and repeats the
upstream link and signing commands. Every other object/archive remains
byte-identical. This is an incremental build, not a claimed clean rebuild;
the normal recipe applies the same patch to a fresh full source tree.

## Isolated runtime acceptance

On 2026-10-08, VirGL trial from OS commit
`9c0b92bea0af2b69fbdfcbf633b7c0be74be650c` was tested with both host binaries.
With the original host, the same scanout fence failed, but the repaired PCI
queue teardown returned consumer failure and halted cleanly without a panic.
This isolates the OS error-path repair from the Cocoa repair. It does not
prove rendering can resume after a live 3D reset.

With this patched host, the same installed Mesa26/LLVM23/wlroots package stack
rendered and presented four 1280x800 frames through the actual DRM backend.
The renderer was `virgl`; all pixel checks, presentation events, provider
guards and cleanup passed. QEMU exited zero and the snapshot input was
unchanged. The host loaded the recorded renderer/frameworks and reported
ANGLE Metal on Apple M3. The final public supervisor repeated the result.
The [wlroots instructions and hashes](../../../profiles/common-graphics/cross/wlroots-virgl.md)
record the accepted bundle and logs.

The default CPU consumer also passed four frames on the original 2D VirtGPU trial
device. These results do not establish application surfaces, input-event
delivery, VT switching, live 3D reset or sustained compositor use.
