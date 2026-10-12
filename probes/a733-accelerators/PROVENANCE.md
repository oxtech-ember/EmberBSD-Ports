# Sources and licenses

The audit was prepared with AI assistance on 2026-10-08. No upstream code or
firmware is copied into this probe. Local C/shell helpers are MIT licensed.

| Source | Pin | Use |
|---|---|---|
| [Mesa archive](https://archive.mesa3d.org/mesa-26.2.4.tar.xz) | 26.2.4 | The project's common graphics release; original etnaviv feature databases and TP implementation |
| [Orange Pi BSP](https://github.com/orangepi-xunlong/linux-orangepi/tree/2ac08e8c7cdc28abbdc5c9a9dd812f887ae9c79f) | `2ac08e8c7cdc28abbdc5c9a9dd812f887ae9c79f` | A733 hardware and platform reference |
| [Linux PowerVR](https://github.com/torvalds/linux/blob/7b63ef2d55f24519e7e9e5f4d15dbea03f126e40/drivers/gpu/drm/imagination/pvr_device.c) | `7b63ef2d55f24519e7e9e5f4d15dbea03f126e40` | Current upstream support classification; research snapshot, not a selected target kernel |
| [Imagination firmware](https://gitlab.freedesktop.org/imagination/linux-firmware/-/blob/8a58f81883f7be458daa34e418cc4079f995b279/powervr/rogue_36.56.104.183_v1.fw) | `8a58f81883f7be458daa34e418cc4079f995b279` | Exact BXM firmware; installed with its license, validated by native firmload, and booted on Zero 3W; one native KCCB command completes; graphics execution remains unverified |

`sources.tsv` gives the SHA256 of every header compiled by the probe and
the Mesa build file that defines its hardware database inputs. The
Mesa archive and common Mesa adaptations are owned by
[`profiles/common-graphics`](../../profiles/common-graphics/README.md).

The six compiled headers each offer a choice of MIT or GPL licensing. Use
their MIT terms for this source audit and retain upstream notices if any
header is later redistributed. The BSP's separate
`aw_nna_galcore/inc/gc_feature_database.h` carries a proprietary notice; it
is not a source to copy into Mesa. Full identity fields can also be found in
the BSP's `gc_vsim_configs.h`; they remain expected identifiers until the
physical hardware is queried.

PowerVR firmware SHA256:

```text
1db1c399c17401d1f79d46c880db81c724d748c784d4639433b076aba2f9c0d2
```

Size: 131,072 bytes. `WHENCE` identifies version `1.1.OS@6976702`.
The [firmware license](https://gitlab.freedesktop.org/imagination/linux-firmware/-/blob/8a58f81883f7be458daa34e418cc4079f995b279/LICENSE.powervr)
permits unmodified binary redistribution subject to its conditions,
including preservation of the copyright and disclaimer and use with
Imagination-designed and licensed products. It prohibits reverse engineering,
decompilation and disassembly. The probe neither modifies nor inspects the
firmware's executable contents.

Relevant original paths:

- BSP `bsp/configs/linux-6.6/sun60iw2p1.dtsi`: NPU `0x03600000`, SPI 65;
  GPU `0x01800000`, SPI 63/64; their clocks, resets and power domains.
- BSP `bsp/drivers/npu/aw_nna_vip/vip2/inc/vip_feature_database.h`:
  PID/revision, NN/TP counts, SRAM, XYDP0 and MMU mode.
- BSP `bsp/drivers/npu/aw_nna_vip/vip2/vip_drv_hardware.c`:
  `vipdrv_hw_pdmode_setup_mmu` and MMU mode selection.
- Mesa `src/etnaviv/drm/etnaviv_gpu.c`: hardware database and fallback.
- Mesa `src/gallium/drivers/etnaviv/etnaviv_ml_tp.c`: TP lowering/emission.
- Mesa `src/gallium/drivers/etnaviv/etnaviv_screen.c`: NN generation selection.

The source audit preserves both the positive identity queries and the
unsupported A733 result. It is not a proposed upstream patch and has not
been submitted or accepted upstream.
