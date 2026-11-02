# Selected PowerVR Services ABI boundary

This is an implementation boundary for the candidate in [README](README.md).
It does not describe a working adapter or a native GPU driver.
The candidate remains DDK `1.11@5516664` from the pinned BSP revision.
The loader fixtures must run before vendor constructors or firmware.

## Native loader and foreign imports

Use the native EmberBSD AArch64 loader and native threads.
The synthetic TLS DSO has no dependency on either libc.
Passing TLS probes only establishes that this ELF mechanism works.
It does not establish musl thread-control-block compatibility.

`RTLD_LOCAL` controls symbol export scope. It does not provide a separate
libc namespace. The binding fixtures test that distinction directly.
Do not load a full musl libc into the native Qt process.
Do not replace native Qt imports or native libc symbols globally.

For the experimental adapter, rewrite incompatible foreign imports into
an explicit namespace. Keep the original blobs and transformation inputs.
Account for every imported symbol and dependency in the selected closure.
Preserve symbol versions and relocation semantics where present.
An unhandled import must stop the experiment before a constructor runs.
Do not use a generic variadic forwarding wrapper.

## Required translation interfaces

The initial ELF audit found pthread, errno, syscall and ioctl imports in
the Services library. Exact wrapper signatures and constants must come
from the selected DDK and its Linux AArch64 musl ABI headers.
The table defines responsibilities; it does not supply guessed layouts.

| Boundary | Required behavior |
| --- | --- |
| TLS and errno | Return thread-local foreign errno storage. Translate numeric errors at each ABI boundary. Preserve the native thread pointer. |
| Thread lifecycle | Translate opaque foreign thread handles. Define callback trampolines and ownership through join or detach. |
| Mutexes and conditions | Decode foreign layouts, initializers and attributes. Keep native synchronization objects in adapter-owned storage. |
| Allocation | Select one allocator for each ownership domain. Free through the allocating domain, including returned vendor buffers. |
| File and directory APIs | Translate flags and foreign `stat`/directory layouts. Never cast native structures into foreign structures. |
| Stdio | Keep foreign `FILE` handles opaque. Route each supported operation through a typed wrapper. |
| Signals and time | Translate layouts, signal numbers and clock identifiers when they differ. |
| Mapping | Translate mapping flags and error results. Track the lifetime of device mappings separately from ordinary memory. |
| `syscall` | Dispatch only identified Linux AArch64 syscall numbers with their exact argument ABI. Reject unimplemented numbers. |
| Device `ioctl` | Translate transport requests and outer layouts. Dispatch only the bridge commands implemented by the native KMD. |
| Unwind and cancellation | Define the compatible runtime and cleanup path before allowing exceptions or cancellation across the boundary. |
| `setjmp`/`longjmp` | Keep jump buffers inside one ABI domain unless an explicit translation is implemented. |

The first experimental leaf is the [errno adapter](ERRNO-ABI.md).
It provides separate foreign TLS storage and explicit error-number translation.
Host checks and AArch64 cross-linking pass. Target and vendor execution of this
component remain pending; the loader does not yet route vendor imports to it.

## Native kernel interface

Port the selected Services KMD through its OS abstraction layer.
Keep the DDK bridge command IDs and payload layouts paired with its userspace.
Do not send the candidate's requests to the unrelated Mesa PowerVR driver.
The KMD and adapter need these concrete interfaces:

1. Per-open connection ownership, bridge dispatch and close cleanup.
2. Checked copies of user payloads, including lengths and embedded handles.
3. GPU virtual-memory allocation, mapping, cache operations and unmapping.
4. Interrupt completion, synchronization waits, timeout and cancellation.
5. A133 power, clocks and reset control with rollback on every failure.
6. The selected firmware loader and Services initialization sequence.

The exact ioctl numbers, bridge structures, mapping offsets, cache rules
and firmware handshake remain source-derived inputs to the KMD port.
No numeric substitute is specified here.
Firmware with a matching BVNC alone does not satisfy this interface.

The [Services DRM envelope decoder](BRIDGE-DRM.md) supplies the selected
outer command's byte format. Host checks and AArch64 cross-linking pass.
It does not copy payloads, perform an ioctl or implement bridge commands.

The [typed Services ioctl core](SERVICES-IOCTL.md) adds explicit command
selection, size checks, callback-based memory copies and transport errors.
Its focused host regression and AArch64 cross-link pass. Real memory backends,
command handlers, fd ownership and foreign import binding remain pending.

The [Connect payload helper](CONNECT-PAYLOAD.md) checks the pinned candidate's
input identity and encodes its packed reply. Native flags, options, connection
lifecycle and handler binding remain pending. It does not invoke ConnectKM.

## First graphics result

After the adapter and KMD work, create a native EGL pbuffer and GLES context
in a temporary diagnostic process. Draw a triangle and verify pixel readback.
Record the renderer and the actual loaded libraries and firmware.
A software renderer cannot establish this hardware result.

Only then connect native EGL to Qt Quick's offscreen rendering path.
The first display route can copy pixels into the existing framebuffer.
Direct scanout and a new display server are separate work.
The active application is not part of this diagnostic process.
