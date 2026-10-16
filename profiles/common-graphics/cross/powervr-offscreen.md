# Bounded PowerVR offscreen graphics check

This consumer checks one 16 by 16 RGBA8 image through the installed PowerVR ICD.
It draws a green triangle over a red clear color. It copies the optimal image
into a host-visible staging buffer. It checks all 256 pixels and surrounding guards.
The consumer uses geometry, fragment and transfer jobs. It uses no WSI surface,
PRIME export, Zink, display mode change or direct device-register access.

## Current boundary

The C consumer, validated SPIR-V and modeled Vulkan contracts pass on the build host.
They do not prove shader execution or physical graphics. The physical test remains pending.
Use the accepted MesaLib 26.2.4nb5 to isolate the kernel transition from Mesa changes.
The kernel must include native `TRANSFER_FRAG` admission and the reviewed graphics series.
See the [OS execution contract](https://github.com/oxtech-ember/EmberBSD/blob/2b617f0e213adcf4dc756c92465b53446bb8e7d2/ember/boot/a733-pvr-execution.md).
This source revision is a local integration dependency until it reaches the main branch.
Do not treat enumeration or the earlier compute result as graphics acceptance.

## Cross-build

Use the common GCC16 compiler, an EmberBSD sysroot and the current native SPIRV-Tools prefix.
Run from a clean committed Ports checkout:

```sh
ruby build-powervr-offscreen.rb /absolute/common-cross-tools \
    /absolute/ember-sysroot /absolute/spirv-tools-prefix /absolute/new-offscreen-check
```

The builder assembles and validates both shaders for Vulkan 1.2.
It records the source revision, commands, compiler dependencies and selected base/link input hashes.
These hashes do not establish the source revision of a complete sysroot.
Transfer the executable and `run-powervr-offscreen.sh` from this output directory.
The executable contains the validated shaders; it needs no external shader files.
After the kernel and package checks, run:

```sh
PVR_I_WANT_A_BROKEN_VULKAN_DRIVER=1 sh run-powervr-offscreen.sh \
    /dev/dri/renderD128 /absolute/new-offscreen-result
```

The runner selects the installed PowerVR ICD and records its loader dependencies.
The consumer requires the Imagination Mesa driver identity and the exact DRM node.
It rejects a missing graphics queue or unsupported optimal RGBA8 transfer format.
Each image or buffer allocation is limited to 16 MiB. The fence wait is ten seconds.
The outer runner limits execution to sixty seconds. A failed submit or uncertain wait
exits without destroying possibly active GPU resources; process teardown owns them.

## Pixel and memory contract

The copy uses a 64-byte prefix, a 20-pixel row stride and an 18-row staging extent.
Pixels outside the 16 by 16 image retain the poison byte. Every image pixel has an
independent expected color from triangle coverage at its pixel center.
Explicit barriers order host writes, color output, transfer reads and host reads.
The entire mapped allocation is flushed and invalidated. Offset zero and whole-allocation
ranges preserve the noncoherent atom alignment requirements.

The Vulkan [copy rules](https://docs.vulkan.org/refpages/latest/refpages/source/vkCmdCopyImageToBuffer.html)
and [buffer-image layout](https://docs.vulkan.org/refpages/latest/refpages/source/VkBufferImageCopy.html)
define the transfer contract. The [invalidate rules](https://docs.vulkan.org/refpages/latest/refpages/source/vkInvalidateMappedMemoryRanges.html)
define when device writes become visible to host reads. No linear-image fallback replaces
this optimal-image path.

## Source checks

Run the actual C consumer against the explicit Vulkan boundary model:

```sh
ruby ../tests/powervr-offscreen.rb /absolute/vulkan-headers/include \
    /absolute/spirv-tools-prefix /absolute/new-contract-check
SANITIZERS=yes ruby ../tests/powervr-offscreen.rb /absolute/vulkan-headers/include \
    /absolute/spirv-tools-prefix /absolute/new-sanitized-check
```

The checks inject failures at every result-returning API call. They cover partial pipeline
creation, uncertain submission, cleanup, stale CPU data and row or guard corruption.
Causal mutants remove invalidation, fence waiting, drawing or the required host barrier.
Other mutants break the node identity, row stride, pixel oracle or mismatch rejection.
The shell runner has a separate host contract in `../tests/powervr-offscreen-runner.rb`.
The model owns separate host and device byte arrays. It does not execute either shader.
ASan/UBSan checks this host model. Valgrind Memcheck is unavailable on macOS ARM64;
these sanitizer checks are not Memcheck results.
