# Native Services binding: provider boundary

The next required component is a native legacy Services KMD provider in
EmberBSD. Another decoder or callback fixture cannot supply that provider.
This document records a source-derived binding plan and an implementation
barrier. It is not an implemented binding or a graphics acceptance result.

## Checked implementation barrier

The checked EmberBSD revision is
`707322954a39edd3e917a9ff7b4a2de8647d671b`.
The following source search returned no matches, with Git exit status 1:

```sh
git grep -n -E 'PVRSRVConnectKM|PVRSRVConnectionConnect|PVRSRV_BRIDGE_PACKAGE|PVRSRVAllocHandle|PVRSRVLookupHandle' \
    707322954a39edd3e917a9ff7b4a2de8647d671b -- sys
```

The existing [native PowerVR driver](https://github.com/oxtech-ember/EmberBSD/blob/707322954a39edd3e917a9ff7b4a2de8647d671b/sys/external/bsd/drm2/powervr/pvr_drv.c)
has a Mesa-facing ioctl table and rejects BVNCs outside its BXM profile.
Its [query profile](https://github.com/oxtech-ember/EmberBSD/blob/707322954a39edd3e917a9ff7b4a2de8647d671b/sys/external/bsd/drm2/powervr/pvr_query.c)
requires BVNC `36.56.104.183` and firmware `1.1.6976702`.
Its GEM/VM ownership code is not a legacy `CONNECTION_DATA` provider.
Do not forward the selected Services request to that driver.

The donor source is available, including its exact `22.102.54.38` core header.
No missing external BSP input was demonstrated by this check.
The current barrier is an internal, unimplemented Services port.
This finding concerns checked source; it does not inventory running modules.

The donor establishes why a file-cookie wrapper is insufficient:

- `PVRSRVConnectionConnect` needs Services global state, OS-private data,
  sync registration, connection/process handle bases, locks and global lists.
- `OSGetDevData` returns a stored, real `PVRSRV_DEVICE_NODE`.
- `PVRSRVConnectKM` immediately uses device configuration and feature callbacks.
- `PVRSRVConnectionDisconnect` queues deferred cleanup with possible retry.

## Concrete native route

The intended route is:

```text
selected foreign ioctl import
  -> typed userspace wrapper: normalize request, call native ioctl
  -> dedicated native Services file object
  -> kernel-owned envelope snapshot and checked nested copies
  -> selected Services connection/device provider
  -> native transport result plus unchanged DDK reply payload
```

The wrapper translates the native transport errno after the native call.
Kernel code returns native transport errors; it does not use libc TLS errno.
The experimental [typed core](SERVICES-IOCTL.md) is a userspace policy prototype.
It is not kernel-linkable binding code and its in-process callbacks do not
cross the kernel boundary. The OS must not depend on `Ports/probes` or libc.
The native UAPI and provider implementation belong in the OS repository.

Use a distinct native Services request; do not reuse the Linux request value.
The 32-byte envelope is input-only: replies use its nested output address.
An `_IOW` native envelope avoids an unnecessary final outer copyout.
The native command number must be defined with the actual implemented UAPI.
No unimplemented command number is assigned here.

This choice follows [native sys_ioctl](https://github.com/oxtech-ember/EmberBSD/blob/707322954a39edd3e917a9ff7b4a2de8647d671b/sys/kern/sys_generic.c):
it copies `IOC_IN` data before `fo_ioctl`, then copies `IOC_OUT` data after
the handler returns. The handler cannot observe that later copyout failure.
Decode the already copied kernel envelope; do not run `copyin` on it again.
Perform the nested 16-byte input copy and 17-byte reply copy inside the handler.
Check user ranges before narrowing addresses; use native `copyin`/`copyout`.
These primitives exist in the checked OS. Their existence does not implement
Services connection creation, handles or GPU virtual memory.

## Ownership and failure policy

Bind the connection to the open file object, not a numeric fd or one PID.
The [native DRM file glue](https://github.com/oxtech-ember/EmberBSD/blob/707322954a39edd3e917a9ff7b4a2de8647d671b/sys/external/bsd/drm2/drm/drm_cdevsw.c)
shows the available `fd_allocfile`, `fd_clone`, `fd_abort` and `fp->f_data`
pattern. Reuse native file-reference semantics, without modifying the Mesa driver.
Duplicated descriptors share an owner; an ioctl holds a live file reference.
Serialize Connect and close with a native mutex and an active-operation drain.
Preserve the donor's required Services-wide synchronization across file owners.
A per-file state lock alone does not protect global Connect state.
Do not hold a non-sleepable lock across user copies or provider calls.

Track `unconnected -> connecting -> connected`, with separate failed/closing
states. Pure precheck failure must not enter the stateful provider.
After provider failure or reply-copyout failure, reject further bridge calls
on that connection and require close/new open. Do not retry Connect implicitly.
An output copy can partially complete; zeroed scratch is not a transaction.
Closing does not promise to reverse global driver-information changes.

Call `PVRSRVConnectionDisconnect` exactly once for a created donor connection.
`PVRSRVDisconnectKM` alone does not destroy it.
Keep the native OS-private owner and device references alive through deferred
destruction and `PVRSRV_ERROR_RETRY`. Do not free them at file close while
the cleanup queue can still reference them. Unwind failed creation in reverse
order, before publishing the owner through the file object.

## Flags, options and capabilities

Derive the accepted client policy from the actual native KMD configuration.
Do not silently clear unsupported bits or force `SRV_NO_HWPERF_CLIENT_STREAM`
to bypass a missing transport-stream implementation.
The donor defines no-stream at bit 4, client-64-bit at bit 5, SLR-disabled
at bit 6 and PDump control at bit 31. Other feature bits also exist.
Their definition does not prove native support or form an acceptance mask.

Compare options using `RGX_BUILD_OPTIONS_MASK_KM` (`0x0000ffff`), the native
`RGX_BUILD_OPTIONS_KM`, `OPTIONS_STRICT` and the selected strict-check policy.
Version/build identity alone is insufficient. No native option value exists
until that provider has an actual configuration.
Reply masks must advertise only implemented native Services/RGX operations.
Construct the reply mask from the native operations actually implemented.

## Smallest real port slice and graphics distance

A real first slice must link a device owner and Services global state with
actual connection, handle, sync and cleanup implementations, plus native
file-private ownership and checked copies. It must resolve these dependencies
against ported code, without fake device nodes or success stubs.
Validate its new allocation/unwind, duplicate/close, concurrent ioctl and
failed-copyout paths. A link or lifecycle test still does not accept hardware.

The first EGL/GLES triangle also needs these real KMD services:

- GE8300 device initialization, power/clock/reset ownership and interrupt delivery.
- PMR allocation, DMA/cache synchronization and GPU virtual-memory mapping.
- Services synchronization objects, waits, cleanup and required memory bridges.
- The selected RGX context/render/transfer command path and completion handling.
- Matched firmware loading, initialization and acknowledged job completion.

The userspace import/dependency closure must work with those exact interfaces.
Only completed GPU work and independent pixel readback can accept the first
offscreen graphics probe. Qt Quick integration follows that result.
No provider, kernel, firmware, vendor or display execution was performed here.
No preceding payload/dispatch/errno test set was repeated.

## Pinned donor evidence

All donor links use revision `7f37a7fbf4ad59907034715e3d967b9177de1cd4`.

- [Connection creation and deferred destruction](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/server/common/connection_server.c).
- [OS-private ownership and device lookup](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/server/env/linux/osconnection_server.c).
- [Stateful Connect and DisconnectKM](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/services/server/common/srvcore.c).
- [Client flags](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/services_km.h)
  and [build-option policy](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/include/rgx_options.h).
- [Exact hardware core header](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/modules/gpu/img-rgx/linux/rogue_km/hwdefs/km/cores/rgxcore_km_22.102.54.38.h).
