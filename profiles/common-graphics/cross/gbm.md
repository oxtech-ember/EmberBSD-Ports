# Common Mesa through native VirtGPU buffers

On 2026-10-08 the canonical MesaLib 26.2.4nb2, libdrm 2.4.134nb1 and
shared LLVM 23.1.2 providers passed a real GBM/PRIME/EGLImage/GLES round
trip in an isolated NetBSD 11/AArch64 VM. This establishes the device-buffer
path needed for the [current wlroots migration](wlroots.md). Rendering used
llvmpipe explicitly; neither guest VirGL nor a visible compositor was tested.

## Reproduce

Build and verify the bundle with [prepare-mesa-dmabuf.rb](prepare-mesa-dmabuf.rb)
as described in [wlroots.md](wlroots.md#first-gate-actual-drm-buffer-interchange).
Use the complete canonical package payloads, including their exact links,
and base NetBSD utilities. No private graphics libraries belong in the bundle.

The accepted VM used the [native EMBERGPU configuration](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/kernel-boot.md),
cross-built with GCC 16.2 from OS commit
`bd1581bffc1da287f793e8b9bad02cfadd7b593a`. Its source export was checked
against all 191,407 tracked blobs after the complete kernel/module build.
The runner used a 384 MiB read-only FFS root, temporary `/tmp`, two virtual
CPUs, 1 GiB RAM, HVF, serial console and no networking. QEMU used snapshot
mode with this synthetic root; no existing VM disk was attached.

```sh
qemu-system-aarch64 -machine virt,accel=hvf -cpu host -m 1024 -smp 2 \
    -display none -serial stdio -no-reboot -snapshot \
    -kernel netbsd-EMBERGPU.img -append 'root=ld4a console=plcom0' \
    -drive file=root.ffs,if=none,format=raw,id=root \
    -device virtio-blk-pci,drive=root -device virtio-gpu-pci \
    -net none -monitor none
```

VirtGPU reported PCI `0000:00:02.0`, one scanout, no VirGL and no capsets.
Select its actual primary node for the runner:

```sh
sh /absolute/bundle/run-mesa-dmabuf.sh /absolute/bundle \
    /dev/dri/card0 /tmp/new-dmabuf-results
```

The accepted host was Apple Silicon macOS. QEMU was the paired UTM
10.0.12 base with the complete 5.0.6 patch series; this test used its plain
2D device and no display frontend. Its host GL renderer was not exercised.
The root carried NetBSD rescue/base tools and verified package payloads;
this was not a full installed desktop or complete current base-system test.

## Result and limits

All package files, link targets and runtime hashes passed before execution.
Both `ldd` and the live loaded-object inventory resolved recorded providers.
The live check runs while GBM, EGL and the imported BO remain alive, so
unrecorded dynamically loaded backends cannot count as accepted providers.
Eight host callback/parser controls passed, including refusal of an extra
`virtio_gpu_gbm.so`; these controls are distinct from the VM result.

All four VM cycles passed: create GBM/EGL, allocate a linear ARGB8888 BO,
export PRIME, import EGLImage, close the export fd, draw a GLES triangle,
finish, compare GLES readback with all 256 CPU-mapped pixels, and clean up.
The actual BO had modifier `0`, stride `256` and offset `0`. The renderer
was `llvmpipe (LLVM 23.1.2, 128 bits)` and EGL was 1.5. The guarded runner
returned 0; the guest unmounted and powered down, and QEMU returned 0.
A preceding direct libepoxy/GBM run also passed four shader/pixel lifecycles.

The round trip reuses the same device and GBM screen. It does not establish
first import of a foreign BO, cross-process producer synchronization, absence
of internal copies, scanout, physical A733 GPU support or sustained operation.
The serial boot has no firmware framebuffer; `console unavailable: -19`
denotes an excluded console handoff, not successful visible output.

## Artifact identities

| Artifact | SHA256 |
| --- | --- |
| EMBERGPU ELF | `196c0577cf341ff58bb8156b55c4b180b7d3cf529512f7b6708143a4f914d761` |
| EMBERGPU native image | `59fbce3866a96e710c3b11beac6586a1016c17a6ed502b2db92f168cba184db3` |
| Guarded DMA-BUF bundle | `b904dced781bbf7d4e610e164486aaa7db311904a2cf5ea37356f290792b6f78` |
| Synthetic FFS root | `ebd1e3e986430f26492e820ff82e7647c9feb817112c515a2df918355c8625c6` |
| QEMU executable | `8f65b7752ce5f4650f780237daeeffe24fdb86a90bfd9230db55346e92dc9159` |
| Complete serial result | `9f9de1fa2420a3096cdd3037df9fd676a228b9ba383eb54b6963f207ba0ee6f6` |

Package identities are retained in [Mesa acceptance](mesa-package.md) and
[libepoxy acceptance](epoxy.md). Logs, binaries and the synthetic root remain
outside Git. NetBSD, Mesa, LLVM and QEMU retain their authorship and licenses.

## Native V3D mode

The current preparer consumes MesaLib 26.2.4nb3. The optional final renderer
argument accepts `V3D` for a native CM5 device, while the default remains
explicit llvmpipe for the earlier VirtGPU comparison. V3D mode forbids the
software override and checks the actual GL renderer before drawing:

```sh
sh /absolute/bundle/run-mesa-dmabuf.sh /absolute/bundle \
    /dev/dri/renderD128 /absolute/new-v3d-logs V3D
```

This requires native PRIME sharing in the matched kernel. The initial CM5
kernel without PRIME rejects the scenario because EGL dma-buf import is
unavailable; a compiled consumer alone does not establish sharing support.
See [current CM5 acceptance](mesa-cm5.md) for the physical result and limits.
