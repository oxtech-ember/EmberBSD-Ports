# Installed Mesa V3D on CM5

MesaLib 26.2.4nb3 enables V3D in the same package as VirGL, softpipe and
LLVM23 llvmpipe. libdrm 2.4.134nb2 maps EmberBSD's immutable platform metadata
to the existing public DRM platform API. It requires no DRM master, primary
open, global PCI access or fabricated PCI IDs. Older kernels keep their
existing discovery; malformed metadata never silently falls back.

The matching [native kernel interface](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/bcm2712-v3d-gl.md)
provides serialized bin/render jobs and binary synchronization. On 2026-10-11,
CM5 Rev 1.0 / BCM2712 D0 (4 GiB, 64 GB eMMC), on Waveshare CM5-NANO-B,
passed actual installed hardware rendering. Existing UEFI was preserved;
its source and carrier PCB revisions remain unknown. The installed base's
revision is not recorded, so this is not full SDK/base-set acceptance.

## Results and limits

- Normal cross-package file, permissions, PIE/RELRO, RPATH and work-reference
  checks pass for complete Mesa and core libdrm. The target sysroot supplies
  EmberBSD ABI inputs and the accepted common GCC16.2/LLVM23.1.2nb1 closure.
- Explicit `/dev/dri/renderD128` and default surfaceless selection both report
  `V3D 7.1.10.2`, EGL 1.5 and OpenGL ES 3.0 without a renderer override.
- Four EGL lifecycles each pass invalid-shader rejection, real shader
  compilation, clear/triangle/outside pixel samples and object teardown.
  The 16x16 and 1280x800 runs both pass. The latter takes 0.19 seconds total;
  this is not a desktop FPS or sustained-load measurement.
- All 38 unchanged upstream invocations pass, including V3D QPU disassembly,
  seven LLVM JIT tests and VirGL staging tests. Utility `Cache.List` skips
  internally; nine upstream NIR cases remain disabled.
- An explicit software comparison passes four llvmpipe/LLVM23 cycles,
  reporting GLES 3.2. That environment override is only a comparison test.

Installed libepoxy 1.5.10nb2 also passes four actual V3D dispatch lifecycles
and all four unconditional upstream tests against this same provider. Its
bundle checks installed hashes, symlinks and the live loader closure; five
corruption/refusal cases and three loader-callback cases pass on the host.
Meson input paths may use a valid build symlink, but are checked by realpath;
other library directories or environment keys remain rejected.

The experimental kernel limits BOs to 16 MiB individually and 64 MiB total.
Same-device linear PRIME sharing is accepted below. Foreign-device sharing,
a virtual Wayland output, remote capture/input, current Qt/KWin/Plasma consumer
migration and sustained desktop use remain unaccepted.
This receipt establishes offscreen hardware GL, not a ready remote desktop.
Vulkan, video encoding and Mesa compute capabilities are not claimed.

## Reproduce

Build the canonical recipes using [the common cross composition](profile.md).
Install their actual packages normally in the sysroot and on the target;
use the matching kernel/module bundle and preserve a verified ordinary bundle.
Build/transfer the [full acceptance bundle](mesa-package.md), verify its hash,
and extract it into a fresh directory. On a CM5 running that kernel:

```sh
sh /absolute/bundle/run-mesa-package-tests.sh \
    /absolute/bundle /absolute/new-test-logs V3D
/absolute/mesa-render /dev/dri/renderD128 V3D 1280 800
```

The optional width/height arguments require the current `mesa-render.c`;
the original default remains 16x16. Dimensions must be integers in 16..4096.
The runner checks every installed package file, link and runtime-library hash.
No private runtime library is bundled. `libdrm-platform-check.c` additionally
checks driver name, platform compatibility, enumeration folding, node type
and the exact render pathname. Compile it against installed libdrm via the
same cross compiler/sysroot, then run it with the render node argument.

## Port repairs and validation

Cppcheck 2.22 with actual target preprocessing found an unchecked
`CALLOC_STRUCT` in Mesa's V3D import path. The patch returns through its
existing mutex-unlock path. The actual upstream body fails under UBSan with
injected allocation failure, then passes ASan/UBSan after the repair.
The regression also covers cached handles, ioctl failure and successful import:

```sh
ruby ../tests/mesa-v3d-oom.rb /absolute/mesa-source /absolute/new-oom-work
SANITIZERS=yes sh ../tests/libdrm-platform.sh /absolute/patched-libdrm-source
```

Six selected V3D units retain 2,817 other Cppcheck findings from expanded
headers/macros and type casts; these are not all individually triaged or
suppressed. The five diagnostics of the confirmed allocation bug disappear.
libdrm's actual preprocessed unit retains the same 14 diagnostic messages
before/after the platform patch. Host contracts test mixed PCI/platform
records, independent node indices, reused/missing nodes, unknown schema,
short records, unterminated strings and permission failures. ASan/UBSan passes.
Valgrind is unavailable on the ARM64 macOS/EmberBSD hosts; no Valgrind pass
is claimed. Host models do not establish hardware concurrency or long-run safety.

The LLVM metadata helper uses the accepted DWP-only package rebinding,
[with unchanged upstream query execution](llvm-config.md). No second LLVM
provider or metadata-response stub is introduced.

## Artifact identities

| Artifact | SHA256 |
| --- | --- |
| MesaLib 26.2.4nb3 | `196f5d33158fd96a84c26d66f9459242cec9afa38f4a183d7f40225721403d79` |
| libdrm 2.4.134nb2 | `9c02cd67cf0702fb55c8f0386781c8980f1af88b29d3b6747636ec118c64ee76` |
| Installed upstream-test bundle | `ae5195644465ff686605571acc3dc26cdc1c0ac8782814a78534566982e3fdfe` |
| Installed libepoxy test bundle | `4344e1b6b1497e24883fa65f9f776736680aa64e8d81e50b1d1e3aa9f4da1c8f` |
| Physical libepoxy V3D log | `fa588def07ac887b18d519b4f5378be57eccafa03fdd9e7af74e759ab3688c88` |
| Initial physical V3D/identity log | `c363b5636f0c24ad52f584214c76d567ff35255b914b024249859271a830b9fe` |

The bundle above contains the original fixed-size consumer; the subsequent
1280x800 run uses the current optional-size consumer. Logs and binaries stay
outside Git. Original Mesa/libdrm source hashes remain in `sources.tsv` and
the recipes' distinfo; all upstream licenses and attribution are preserved.

## Physical shared-buffer acceptance

With native kernel commit `78c6715a949`, the same installed packages pass four
GBM/PRIME/EGLImage/GLES cycles on V3D 7.1.10.2. Each creates a linear ARGB8888
BO, exports/imports its fd, closes the export fd, draws a real GLES triangle,
finishes, compares every one of 256 CPU-mapped pixels with GPU readback, and
cleans up. The live-provider inventory and package manifests pass. Four
subsequent 1280x800 ordinary render lifecycles pass too. Run the
[explicit V3D mode](gbm.md#native-v3d-mode) to reproduce it.

The kernel's separate checker passes 80 SCM_RIGHTS/duplicate-import/mmap
lifecycles in 0.07 seconds. It first exposed native DMA-BUF reference leaks;
those repairs and actual-source regressions belong to the
[OS receipt](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/bcm2712-v3d-gl.md#physical-prime-acceptance-2026-10-11).
This does not establish foreign-device DMA, arbitrary modifiers or remote UI.

DMA-BUF bundle SHA256: `d00a2880ad5dd397eebd4e521ecafb608750b954d81dd4f6bb06c318dace2800`.
Physical Mesa PRIME/1280x800 log SHA256: `f147b8050b4ad7743ea2d945056ae49855bbf9c4c987913e2194f17851df945e`.
The unchanged default helper policy still selects explicit llvmpipe for the
older VM comparison. V3D mode rejects software overrides and checks the
actual renderer. Three callback and five provider-refusal controls pass.
