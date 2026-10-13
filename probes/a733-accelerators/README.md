# A733 accelerator source audit

This probe identifies the concrete gaps between the Allwinner A733 BSP and
Mesa's open NPU stack. It does not enable GPU/NPU hardware. It helps avoid
selecting an incompatible userspace or treating a device node as acceleration.

The physical target is Orange Pi Zero 3W with A733. EmberBSD now supplies
native power and clock providers. The [GPU PLL and identity check](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-identification.md#physical-pll-result)
reads BVNC `36.56.104.183` after strict CORE ON/Q readiness.
The [native firmware preflight](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-fwinfo.md#physical-preflight-result)
reads the matching firmware and validates its metadata on the board.
The [native memory preparer](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-fwmem.md#physical-preparation-result)
also passes on the board. The [native firmware bootstrap](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-fwboot.md#physical-bootstrap-result)
now executes firmware on Zero 3W. It reports startup and matching hardware/firmware
BVNC through direct coherent memory. The [LOGTYPE and MMUCACHE commands](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-fwprobe.md#physical-command-result)
also complete with verified return words, queue progress and executed-command counters.
All firmware allocations remain device-owned.
The [native compute check](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-gpu-fwcompute.md#physical-stages-19-21-result)
now passes stages 1–21 with this Mesa producer. The GPU writes `0x13579bdf`;
client queue, timeline, and fresh fault checks agree. This is one bounded
dispatch after a fresh boot. PowerVR DRM, rendering, and accelerated Plasma
remain unverified. Precreated `/dev/dri` nodes do not show an attached driver. The source audit below remains separate from hardware
acceptance of the full accelerator stack.

## Reproduce the source check

Use Mesa **26.2.4**, the common graphics version, and Orange Pi's Linux BSP
revision **2ac08e8c7cdc28abbdc5c9a9dd812f887ae9c79f**. The BSP is a hardware
reference, not an alternative target kernel or a new runtime dependency.
Obtain the original sources using [the provenance links](PROVENANCE.md).

```sh
sh audit.sh /path/to/mesa-26.2.4 /path/to/linux-orangepi /private/build/a733-audit
```

The output directory must not exist; its parent directory must exist.
The helper refuses to reuse an existing output directory.

The shell helper verifies SHA256 before compiling the original vendor and
Mesa headers. It executes the original Mesa lookup functions, including
their masked matching of informal revisions. Seventeen existing NPU
identities are positive controls. All five databases listed by Mesa's
`src/etnaviv/hwdb/meson.build` are checked; that file is also pinned and its
input list is compared with the audit manifest. No Mesa generator, Python,
driver, model runtime, or target hardware is needed for this check.

Verified on macOS/arm64 with Apple Clang on 2026-10-08:

| Source result | Value |
|---|---|
| Vendor PID / revision | `0x1000003b` / `0x9202` |
| NN engines / TP engines | 8 / 0 |
| Internal SRAM in the feature table | 524,288 bytes |
| NN XYDP0 / MMU page-descriptor mode | 1 / 1 |
| Mesa hardware databases | A733 identity and PID absent in all five |
| Existing NPU lookup controls | 17 successful queries |

This is source evidence. It does not measure the SRAM available to a model,
prove a complete Mesa build, or establish DMA or inference on the board.

## NPU: adding an identifier is insufficient

The BSP calls this family VIP9000 NanoDI Plus. Its expected complete identity
is model `0x9000`, revision `0x9202`, product `0x05090009`, ECO `0x08000000`,
customer/PID `0x1000003b`. Confirm those fields from hardware before matching
a driver. The independently licensed VIP2 feature table supplies the count
and MMU facts above; the larger galcore table is not imported.

[Teflon's documented tested Vivante targets](https://docs.mesa3d.org/teflon.html)
are VIPNano-QI.7120 in A311D and VIPNano-SI+.8002 in i.MX8M Plus. Mesa's
`etnaviv_gpu.c` uses the feature database to identify NPU cores. Its fallback
only sets GPU features and limits. Consequently a missing NPU record does
not produce a usable generic NPU target.

Mesa chooses its V8 NN path when `NN_XYDP0` is set. That alone is not an
A733 implementation. `etnaviv_ml_tp.c` emits TP instructions for transpose,
padding, reshuffling and activation operations. Its emission loop is bounded
by `tp_core_count`; the A733 table reports zero. Before enabling this hardware,
these operations need a validated alternative or explicit rejection. A fake
TP count would issue commands for a capability not established by the source.

The VIP2 kernel also selects a separate MMU page-descriptor initialization
path for this PID. `vipdrv_hw_pdmode_setup_mmu` programs the page descriptor
directly, unlike the alternate command-buffer initialization. Linux
etnaviv's existing MMUv2 and NetBSD's DMA interfaces need a corresponding
hardware review; the ordinary etnaviv UAPI is not the vendor VIPLite ABI.

A complete native path therefore needs:

1. Power-aware register identification through the native EmberBSD A733
   PCK600, clock/reset and FDT providers. Record the exact accepted NPU
   fields before selecting the complete hardware description.
2. Buffer ownership, DMA/cache synchronization, NPU MMU, IRQ completion,
   bounded waits, reset, and cleanup after process death in the OS repository.
3. A licensed Mesa feature description and A733-compatible command lowering,
   including the missing TP path, in Ports. Keep the common Mesa version.
4. A native TFLite-compatible runtime with Teflon, then a small quantized
   Conv/ReLU graph with CPU comparison and explicit delegation accounting.

The vendor route still needs a native userspace implementation: Linux
`libVIPhal.so` and `libNBGlinker.so` cannot become a NetBSD runtime by compiling
the available VIP2 kernel code. Teflon is an open alternative worth extending,
but A733 inference is not currently validated by either route in EmberBSD.

## GPU: the exact firmware is available

The BSP fixes BXM BVNC `36.56.104.183`. Mesa 26.2.4 lists that exact part as
under active development. Its [Vulkan 1.2 conformance](https://docs.mesa3d.org/drivers/powervr.html)
belongs to different BXM BVNC `36.52.104.182`.

Imagination publishes `powervr/rogue_36.56.104.183_v1.fw`, version
`1.1.OS@6976702`. The pinned 131,072-byte firmware was downloaded and its
SHA256 verified; [provenance](PROVENANCE.md) records the digest and license.
Firmware availability is therefore not the open GPU path's missing piece.

Linux PowerVR at `7b63ef2d55f24519e7e9e5f4d15dbea03f126e40` classifies this
BVNC as unknown. Its `exp_hw_support` flag bypasses the rejection; it is not
hardware acceptance. Port the open PowerVR DRM interface together with
firmware loading, memory management, synchronization and A733 power/clock
integration before using Mesa. The vendor `pvrsrvkm` Services ABI is different.

Start with Vulkan dispatch/readback after identity and firmware initialization.
Zink/OpenGL and a display compositor come after that test. A GPU firmware
download, Mesa build, or successful Linux vendor example proves neither the
native driver nor physical GPU execution under EmberBSD.

Kernel work belongs in [EmberBSD](https://github.com/oxtech-ember/EmberBSD);
model and Vulkan demonstrations belong in
[Examples](https://github.com/oxtech-ember/EmberBSD-Examples).
