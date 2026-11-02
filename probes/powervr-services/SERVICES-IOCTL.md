# Typed Services ioctl core

`adapter/services_ioctl.c` composes the envelope decoder and errno adapter.
It supplies a checked, non-variadic dispatch core for the future foreign
ioctl wrapper. It does not replace the foreign `ioctl` import yet.
No real device handler, file-descriptor registry or memory backend is included.

The [native binding plan](NATIVE-BINDING.md) defines the actual kernel boundary.
This userspace policy prototype uses libc TLS errno and in-process callbacks.
It is not kernel-linkable code or an existing Services provider.

## Call boundary

`pvr_abi_services_ioctl(services, request, argument)` takes trusted native
configuration, a zero-extended Linux request and an opaque foreign address.
The selected [32-byte DRM envelope](BRIDGE-DRM.md) is the only accepted request.
The caller must select a live connection owned by the calling file descriptor.
This core does not create, look up, reference-count or close that connection.

The configuration contains an explicit command table, checked memory-copy
callbacks and separate native input/output scratch buffers.
The table pairs a bridge group and function ID with exact input/output sizes
and a handler. No command is allowed unless it has one matching entry.
An empty table rejects all commands; ambiguous matching entries are invalid.
No production command table is supplied by this change.

Configuration, callback code and connection ownership remain valid for the
whole call. Each call needs private, disjoint scratch buffers with the stated
capacities. They must not alias the configuration, table or foreign memory.
Concurrent calls must not share writable scratch storage without serialization.
The core does not retain pointers or allocate storage.

## Checked sequence

1. Reject an unsupported request before reading foreign memory.
2. Check configuration and the outer address range; copy the envelope once.
3. Decode that snapshot and find exactly one allowed command.
4. Require exact wire sizes, sufficient scratch capacities and valid buffers.
5. Reject null nonempty ranges and unsigned 64-bit range overflow.
6. Copy the input into native scratch through the checked memory callback.
7. Clear output scratch, then invoke the handler for the selected connection.
8. Copy output only after a successful transport result.

Zero-length payloads require no memory access and give the handler null
pointers. Nonzero addresses remain 64-bit integers until the memory backend
checks them. The core does not cast them into native pointers.
Canonical userspace ranges, permissions and access faults belong to that
backend. Embedded pointers and handles need command-specific validation.
An outer range check does not establish payload safety or GPU compatibility.

## Results and failure handling

The memory callbacks and handler return zero or a positive native libc errno.
They must not use `PVRSRV_ERROR` as a transport result or write foreign errno.
A DDK error stays encoded in the command's output payload.
For example, a handler can return transport success with a nonzero DDK error
in that payload; the core copies the payload without interpreting it.

The core returns zero on success and leaves foreign TLS errno unchanged.
On failure it returns -1 and sets foreign errno through the existing adapter.
Native errno is restored to its entry value on every return.
Unsupported native errors and malformed negative callback results become
Linux EIO (5). No internal unsupported-translation sentinel reaches the caller.
EINTR and EAGAIN are returned without an internal retry loop.

The local rejection policy uses ENOTTY for unsupported requests/commands,
EBADF for a missing connection, EINVAL for invalid configuration/sizes, and
EFAULT for an invalid nonempty address range. These become Linux numbers.
This experimental policy does not establish donor command-specific behavior.

No handler runs after an input-copy failure or failed command validation.
No output copy runs after a handler transport failure.
A failing output copy may have written part of the foreign output buffer.
The handler has already run at that point; the core cannot undo its effects.
Real handlers must define resource cleanup and failed-copyout recovery before
integration. This core is not a transaction manager or a complete KMD.

## Focused regression

Build `adapter/services_ioctl.c`, `adapter/bridge_drm.c`,
`adapter/errno_abi.c` and `tests/services_ioctl.c` with the selected SDK C tools.
Use `-std=c11 -O2 -Wall -Wextra -Werror` and explicit host or target inputs.
The host memory backend copies bytes in a bounded array above address 2^32.
The synthetic handler transforms input bytes and writes a payload error.
It performs no system call or device operation.

On 2026-11-02 the normal and ASan/UBSan host consumers passed 141 checks.
They cover successful copies, zeroed output padding, exact command selection,
rejection before dispatch, sizes/capacities, address overflow, null arguments,
copy failures, transport errors, partial copyout and native errno preservation.
The nonzero payload error remains distinct from transport failure.
The empty-payload case performs no payload copy.

Two isolated implementation mutations produced expected check-failure exit 65:
omitting output clearing and omitting exact payload-size checks.
Cppcheck and target-configured Clang Static Analyzer passed for the new core
and consumer. The consumer cross-linked for EmberBSD AArch64.
Valgrind was unavailable in the selected prefix and was not run.

The earlier 312 decoder and 476 errno checks were not rerun.
Their unchanged source components were linked into this new focused consumer.
No consumer ran on a tablet. No vendor constructor, firmware, kernel,
display, network or active application was accessed or changed.
This result establishes source/host behavior and cross-linking only.
Hardware EGL/GLES acceleration remains unproven.
