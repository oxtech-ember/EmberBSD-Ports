# Accelerated wlroots DRM presentation on VirGL

The installed [DRM/input package](drm-input.md) now renders and presents four
1280x800 frames with Mesa's `virgl` renderer in an isolated AArch64 QEMU/HVF
guest. The paired host executes through ANGLE Metal on Apple M3. This extends
the [offscreen guest acceptance](virgl-draw.md) to real DRM output presentation.
It does not yet qualify a desktop or application surfaces.

## Matched inputs and execution

Use MesaLib 26.2.4nb2, libdrm 2.4.134nb1, LLVM 23.1.2nb1 and the canonical
wlroots 0.20.2nb4 `drm-gles2` package, with the seventeen-provider bundle
prepared by [prepare-wlroots-drm.rb](prepare-wlroots-drm.rb). The consumer adds
an explicit renderer policy; the installed library payload is unchanged.
Every package file, link and recursive runtime provider is verified.

The guest needs the separate [VirGL trial kernel](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/docs/utm-virgl-optin.md)
including OS commit `9c0b92bea0af2b69fbdfcbf633b7c0be74be650c` or its descendant.
Keep a matched recovery bundle. This commit fixes modern PCI queue disable
after child teardown; it does not change GPU feature or DMA safety policy.
The paired [QEMU recipe](../../../probes/utm-virgl-host/qemu/README.md) must
include the [Cocoa context repair](../../../probes/utm-virgl-host/qemu/cocoa-context.md).
Keep the accepted renderer and ANGLE framework inputs from that recipe.

Prepare a private synthetic root with the full package bundle and required
base tools. Supply real DRM, wscons keyboard/mouse nodes and a running seatd.
The serial-console acceptance uses `SEATD_VTBOUND=0`; it does not test VT
switching. Do not select the zero-input-device override. Its boot script runs:

```sh
echo EMBER_WLROOTS_DRM_BEGIN
sh /tests/drm/run-wlroots-drm.sh /tests/drm /dev/dri/card0 /tmp/drm-logs virgl
result=$?
echo "EMBER_WLROOTS_DRM_EXIT=$result"
# Stop the private seatd service and collect its log here.
echo EMBER_WLROOTS_DRM_END
halt -p
```

Preserve the runner's exit status even when collecting logs or shutting down.
The runner clears inherited loader/render settings, forbids software flags
for VirGL and checks the actual renderer before allocation or modesetting.
No failed hardware run becomes a software-rendering success.

From the Ports root, run the public host supervisor:

```sh
ruby probes/utm-virgl-host/qemu/run-guest-draw.rb \
    /absolute/accepted-qemu-work /absolute/accepted-renderer-work \
    /absolute/netbsd-VIRGL_TRIAL.img /absolute/private-root.ffs \
    /absolute/ANGLE-frameworks /absolute/new-drm-evidence wlroots-virgl
```

The optional final argument selects the DRM oracle and adds actual QEMU USB
keyboard/mouse devices. Omission retains the four-cycle offscreen workload.
Both modes verify build receipts, loaded host libraries, the Metal renderer,
unchanged input hashes, normal QEMU exit and bounded output. The guest uses
snapshot mode with no network or monitor. Limits are 120+5 seconds for the
host and 60+5 seconds for the target consumer. Use a private test image.

## Accepted result and controls

On 2026-10-08, the exact matched kernel and patched host passed twice, including
the final public supervisor. Each run recorded renderer `virgl`, four frames
1..4 with presentation sequences 2..5 and flags `0xf`, and 1024 checked GLES2
pixels per frame. The libseat session was active and two actual wscons devices
were enumerated. Package and live-provider guards passed; the consumer and
QEMU exited zero, and the input filesystem remained unchanged.

The kernel's extracted-production queue regression also passed natively in
the guest: 192 cases with assertions and 192 without. Before the Cocoa fix,
the same new kernel returned the render error and halted cleanly after the
failed scanout fence. The old kernel had panicked on the same error path.
This verifies safe teardown for that observed failure, not resumed rendering
or arbitrary in-flight GPU reset recovery.

The unchanged default CPU policy passed four frames on the original 2D
VirtGPU trial device, with `llvmpipe (LLVM 23.1.2, 128 bits)`. On the VirGL device,
Mesa may select VirGL despite the CPU policy's software environment flags;
the actual-renderer check refused that mismatched run before modesetting.
The CPU mode is an explicit acceptance policy, not a guaranteed force switch
for every DRM driver.

| Evidence | SHA256 |
| --- | --- |
| VirGL trial image | `ddec33e6e1f438bb0223322b5fd37803f870e341ee927ae8f223cf5e95b3ac5f` |
| Patched paired QEMU | `8643e589608c24519578c7707b3d2263f4293c4062116a4edbf94f6bb4cbef09` |
| DRM consumer bundle | `06f75c4bf5426350818af7bfc95bf898948ca34bb833509cc9c4fa400ff92118` |
| Final VirGL guest log | `7f19532e2ed677f8d698453cf3654bd080eb4ad08529506a6a3e37edfbef23a0` |
| Final Metal host log | `52106392efea9b08752f8b6f42490de51bf941ad5d134674c57b4a476ef8c497` |
| Final output manifest | `8f066b24355e049d99a5a9d18eb41eed02fd31065a24f17e79d03bf430db5713` |
| CPU regression guest log | `0f93ab499679fd1e01e69e0e3832090e4a4e33f0df9de69bf4735ba7999dbf6c` |

[The later labwc session check](labwc-session.md) covers application surfaces,
screencopy and actual USB input in two sessions on Apple M4. This earlier
enumeration result alone does not establish interactive input. VT switching,
sustained operation, physical A733/CM5 GPU drivers and Vulkan Compute remain
separate acceptance stages.
