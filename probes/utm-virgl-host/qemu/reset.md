# Isolated reset with live 2D backing

This Ports check boots an isolated VirtGPU trial guest and performs three actual
QMP system resets while a guest process owns a dumb GEM resource and mmap.
The fourth boot also holds a resource when QMP quits the process. It exercises
the complete patched QEMU and renderer on ANGLE Metal. It is not an in-flight
3D draw, display-block, memory non-aliasing or no-touch-after-revoke proof.

Use the [built QEMU and renderer](README.md), the matched VirtGPU trial kernel and
a separate 64 MiB FFS root prepared by the
[kernel boot method](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/external/bsd/drm2/virtio/kernel-boot.md).
Never provide an existing VM disk. No guest account or network is needed.
The QEMU profile is enabled only for this experiment; guest VirGL stays off.

Cross-build [guest-hold.c](guest-hold.c) with the accepted GCC16 toolchain,
target sysroot and [libdrm staging](../../../profiles/common-graphics/cross/README.md).
The variables below name absolute private input directories:

```sh
"$cross/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
  -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
  -Wall -Wextra -Werror -O2 \
  -I"$drm_stage/usr/pkg/include" -I"$drm_stage/usr/pkg/include/libdrm" \
  guest-hold.c -L"$drm_stage/usr/pkg/lib" \
  -L"$sysroot/usr/pkg/gcc16/lib" -ldrm -lpci -o "$root_tree/guest-hold"
```

The temporary root needs the target loader, libc, libpci and this libdrm in
`/tests` or `/usr/lib`, plus the documented device nodes. Keep its `/etc/rc`
minimal and the filesystem read-only:

```sh
#!/bin/sh
LD_LIBRARY_PATH=/tests:/usr/lib /guest-hold
echo EMBERGPU_HOLD_FAILED
/rescue/halt -p
```

The process reports readiness only after CREATE_DUMB, MAP_DUMB, mmap and a
sentinel write. It retains both fd and mapping. A 30-second deadline fails if
the controller does not reset/quit it. No scanout or GPU command is submitted.
When copying a rescue root, preserve hard links (for example with tar); copies
that expand every rescue alias may exceed the image size. Generate a fresh
FFS image with the matched `nbmakefs` and target device specification.

Run on a Mac with physical GPU access, using simple absolute paths:

```sh
ruby test-reset.rb /absolute/private/qemu-work /absolute/private/renderer-work \
  /absolute/private/netbsd-VIRTGPU_TRIAL.img /absolute/private/reset-root.ffs \
  /absolute/path/to/UTM.app/Contents/Frameworks /absolute/private/new-reset-run
```

The helper verifies QEMU/renderer binary receipts before starting. It selects
the requested renderer via a private library path, allowing an ABI-compatible
renderer rebuild without changing the QEMU executable. Actual DSO and ANGLE
framework paths are checked in the loader log. Other loader overrides are
cleared. Kernel, FFS and framework hashes are recorded; the input FFS hash must
remain unchanged under `-snapshot`. The guest has no network or shared folders.
Only this helper's child process is reset or terminated; waits are bounded.

On 2026-10-07, GCC16/AArch64 guest code with libdrm 2.4.134nb1 passed on Apple M3.
QEMU 10.0.12-utm with the full UTM overlay and Ports classic patches booted four
times, each reaching live-backing readiness. The complete renderer with the
truncated-command fix reported four ANGLE Metal initializations. Three real
resets and final quit passed; the input image was unchanged. The final read-only
root produced no unclean-filesystem warning. QEMU's checked binary SHA remains
the one in [the build receipt](README.md); the new renderer DSO is recorded
separately by this run.

This short check does not measure resource leaks or prove every cleanup path.
The missing firmware-console handoff and absent ARB/KHR robustness remain
visible limitations. Live 3D commands, pending query writes, blocked display
cleanup and fault injection still require their own runtime acceptance.
