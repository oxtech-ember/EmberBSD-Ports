# Experimental Services DRM envelope decoder

`adapter/bridge_drm.c` decodes the selected DDK's outer DRM command.
It does not issue an ioctl, copy a user payload or dispatch a bridge function.
It is a source-level component for the native adapter and KMD boundary.

## Selected wire format

The pinned DDK defines `drm_pvr_srvkm_cmd` in `include/drm/pvr_drm.h`.
Its Linux AArch64 ioctl request is `0xc0206440`; its size is 32 bytes.
The bytes are little-endian on the selected AArch64 userspace.

| Byte offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | Bridge group ID |
| 4 | 4 | Function ID within the group |
| 8 | 8 | Input address |
| 16 | 8 | Output address |
| 24 | 4 | Input byte count |
| 28 | 4 | Output byte count |

The selected musl fbdev `libsrv_um.so` confirms this outer format.
Its `PVRSRVBridgeCall` starts at ELF address `0x164d0`.
Instructions at `0x164e4` and `0x164fc` form request `0xc0206440`.
Stores at `0x16500`, `0x16504` and `0x16508` fill the fields above.
The call at `0x1651c` passes that request and buffer to `ioctl@plt`.
This is static disassembly evidence; the library was not executed.

The KMD's `PVRSRV_BridgeDispatchKM` receives this DRM structure.
It builds a separate internal `PVRSRV_BRIDGE_PACKAGE` before dispatch.
That internal structure contains native pointers and a size field.
It must not be substituted for the outer 32-byte wire format.
The Linux request value must not be forwarded as a native BSD ioctl number.

## Decoder contract

`pvr_abi_bridge_drm_decode(request, bytes, length, out)` checks the request
first, then requires non-null arguments and exactly 32 readable bytes.
The request is a zero-extended Linux 32-bit number in a `uint64_t`.
A future typed import wrapper must normalize its foreign request argument
according to the actual calling signature before using this interface.
No variadic wrapper or request-argument normalization is implemented here.

The decoder reads bytes without alignment-dependent structure casts.
It stores the six decoded values in `pvr_abi_bridge_command` on success.
On failure it leaves the output unchanged. It does not change native errno.
Return values are internal decoder statuses, not libc or DDK error numbers.

Addresses remain opaque integers. No address is dereferenced or narrowed.
Zero and maximum values can decode successfully; success means format only.
Command authorization, payload limits, address-range checks, checked user
copies, embedded handles and connection ownership still need native KMD work.
No bridge command is implemented or authorized by this decoder.

## Checks

Build `adapter/bridge_drm.c` and `tests/bridge_drm.c` together with the selected
SDK C compiler and `-std=c11 -O2 -Wall -Wextra -Werror`.
Select host or native target inputs explicitly; the decoder has no Linux
header dependency. The instrumented host build adds
`-fsanitize=address,undefined -fno-omit-frame-pointer`.

On 2026-11-02 the Linux x86_64 host consumer passed 312 checks.
The ASan/UBSan consumer passed the same checks without diagnostics.
They cover field offsets, byte order, 64-bit values, unaligned input,
exact length, null arguments, output preservation and every request bit.
Two isolated mutations failed with expected exit 65:
truncated addresses and ignored request bits above bit 31.
Cppcheck and target-configured Clang Static Analyzer passed.

A separate conformance consumer used the pinned `pvr_drm.h` declaration
and Linux generic ioctl macros. It checked the six offsets, size and request,
then decoded an instance of that upstream structure successfully on the host.
The Linux-only header prerequisites were supplied as fixed-width types and
the constants from `pvr_drm_core.h`; this was not a full Linux header build.
The normal and conformance consumers also cross-linked for EmberBSD AArch64.
Neither consumer ran on the target. Valgrind was unavailable and was not run.
No device, vendor constructor, firmware, kernel or display state was accessed.

## Pinned sources

All BSP paths below use revision
`7f37a7fbf4ad59907034715e3d967b9177de1cd4`, DDK `1.11@5516664`.

- [Outer command declaration](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/drm/pvr_drm.h).
- [DRM request macros](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/drm/pvr_drm_core.h)
  and [Linux generic ioctl encoding](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/include/uapi/asm-generic/ioctl.h).
- [Kernel DRM dispatch](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/server/env/linux/pvr_bridge_k.c)
  and [internal bridge package](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/include/pvr_bridge.h).
- [Selected userspace binary](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/package/libs/libgpu/ge8300/fbdev/musl/lib64/libsrv_um.so).

The decoder and unit consumer are original BSD-licensed code.
The upstream declarations and binary remain reference inputs.
