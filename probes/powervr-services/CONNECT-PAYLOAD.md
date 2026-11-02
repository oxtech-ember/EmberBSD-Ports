# Selected Services Connect payload

`adapter/connect_payload.c` implements a pure input check and reply encoder
for the selected DDK's SRVCORE Connect command: bridge group 1, function 0.
It does not register a command handler or call `PVRSRVConnectKM`.
It performs no allocation, memory-backend access or device operation.

## Wire layouts

The input is exactly 16 little-endian bytes:

| Byte offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | Client flags |
| 4 | 4 | Client build options |
| 8 | 4 | Packed DDK version |
| 12 | 4 | DDK build |

`pvr_abi_connect_read_candidate` requires version `0x0001000b` (1.11)
and build `5516664`. It preserves the output on rejection.
Its statuses are internal check results, not Linux errno or DDK errors.
Flags and build options remain raw values; success does not authorize them.
No interpretation of embedded pointers is needed for these four integer fields.

The build check deliberately requires the exact selected candidate.
The donor requires a matching build only with `PVRSRV_STRICT_COMPAT_CHECK`;
otherwise it can warn and continue. This experimental check is stricter.
It does not claim complete donor compatibility checking.

The packed output is exactly 17 little-endian bytes:

| Byte offset | Size | Field |
| --- | --- | --- |
| 0 | 1 | Kernel architecture |
| 1 | 4 | Capability flags |
| 5 | 4 | PVR bridge mask |
| 9 | 4 | RGX bridge mask |
| 13 | 4 | DDK `PVRSRV_ERROR` |

`pvr_abi_connect_write_reply` encodes supplied native values at those offsets.
It requires non-null arguments and exactly 17 writable destination bytes.
On rejected arguments it keeps the destination unchanged.
It preserves the supplied error bits without errno translation.
It does not validate error membership, architecture or capability claims.
Those values must come from the actual native handler.
Neither function uses a native structure as a foreign-memory overlay.
Neither function changes native errno.

## Native KMD binding boundary

A future handler in the [typed ioctl core](SERVICES-IOCTL.md) must:

1. Require the exact 16-byte input and 17-byte output sizes.
2. Check candidate identity before entering the native Connect backend.
3. Validate flags and masked build options against that backend's real profile.
4. Hold a live connection reference and define cleanup for failure/copyout.
5. Derive reply masks and capabilities from implemented native services.
6. Map internal check failures to the selected DDK payload errors explicitly.

The selected `PVRSRVConnectKM` is not a read-only compatibility query.
It updates connection flags and driver information before version checking.
Its client-stream path can allocate a stream before the build check.
Calling that function to discover compatibility would already enter stateful
driver code. The pure helper in this change never calls it.

The KMD build-option mask, strict-option policy and supported client flags
are not supplied here. They depend on the actual native driver configuration.
The donor's advertised bridge masks cannot establish native implementation.
No Connect handler is added to a production command table by this change.
Firmware pairing, fd ownership, memory backend and real connection lifecycle
remain separate requirements before vendor or KMD execution.

## Focused checks

Build `adapter/connect_payload.c` and `tests/connect_payload.c` with the selected
SDK C compiler, explicit host/target inputs, and
`-std=c11 -O2 -Wall -Wextra -Werror`.
The host instrumented build adds
`-fsanitize=address,undefined -fno-omit-frame-pointer`.

On 2026-11-02 the normal and instrumented host consumers passed 133 checks.
They cover candidate identity, byte order, unaligned input/output, lengths,
null arguments, output preservation, packed reply offsets and errno preservation.
Two isolated mutations returned the expected failure exit 65:
omitted build validation and a reply-error field shifted to byte 12.
Cppcheck and target-configured Clang Static Analyzer passed.

A separate consumer compiled the two exact upstream Connect declarations,
the pinned DDK error enum and version definitions. It checked input/output
sizes, every field offset, enum width and candidate version/build.
Its host run decoded an upstream input and encoded an identical upstream reply.
The normal and conformance consumers also cross-linked for EmberBSD AArch64.
No consumer ran on a tablet. Valgrind was unavailable and was not run.
The preceding 141, 312 and 476 test sets were not rerun.
This is source/host/cross-link evidence, not physical GPU acceleration.

## Pinned sources

All paths use BSP revision `7f37a7fbf4ad59907034715e3d967b9177de1cd4`.

- [Connect payload declarations](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/generated/srvcore_bridge/common_srvcore_bridge.h)
  and [generated handler](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/generated/srvcore_bridge/server_srvcore_bridge.c).
- [Connect backend and compatibility checks](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/server/common/srvcore.c).
- [Version definitions](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/pvrversion.h),
  [DDK error enum](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/pvrsrv_error.h)
  and [error members](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/pvrsrv_errors.h).

The helper and unit consumer are original BSD-licensed code.
The upstream declarations remain reference inputs with their original notices.
