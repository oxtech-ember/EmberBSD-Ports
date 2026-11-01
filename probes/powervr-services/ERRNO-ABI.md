# Experimental errno adapter

`adapter/errno_abi.c` is the first small ABI adapter component.
It provides foreign error storage and native-to-Linux error translation.
It does not implement system calls or load vendor libraries.

## Interface

| Native export | Contract |
| --- | --- |
| `pvr_abi_errno_location()` | Return this thread's writable foreign `int` slot. Its initial value is zero. |
| `pvr_abi_errno_from_native(error)` | Return the Linux error number, including zero, or -1 when unsupported. Keep both errno slots unchanged. |
| `pvr_abi_errno_set_native(error)` | Store a supported translation and return zero. On unsupported input, return -1 and leave both slots unchanged. |

The foreign slot is distinct from the native libc errno slot.
Callers must use the pointer only in its owning thread while the module
remains loaded. An explicit setter call with zero clears the foreign slot.
The module does not replace a native libc symbol or change the thread pointer.
Its three exported functions use the `pvr_abi_` namespace.

For a future import transformation, the musl `__errno_location` import can
select `pvr_abi_errno_location`. That transformation is not implemented here.
Other imports and their dependency closure still need their own adapters.

Capture a native error immediately after the failing native operation.
Pass that value to the adapter. A -1 adapter result is an internal unsupported
translation, not a translated foreign syscall result. A future typed wrapper
must handle that condition before returning control to vendor code.
Do not pass a negative kernel return value as a positive libc errno number.

## Error domain

Linux values follow the selected BSP's AArch64 generic UAPI.
The implementation maps matching symbolic errors, not numeric identities.
The input domain is native libc errno. DDK `PVRSRV_ERROR` values belong to
the Services bridge protocol and must retain their own encoding.
For example, native EmberBSD `EAGAIN` is 35 while the foreign result is 11.
Native `EDEADLK` is 11 while the foreign result is 35.
Both native `ENOTSUP` and `EOPNOTSUPP` map to Linux 95.

Native-only errors are deliberately unsupported:
`EAUTH`, `EBADRPC`, `EFTYPE`, `ENEEDAUTH`, `ENOATTR`, `EPROCLIM`,
`EPROCUNAVAIL`, `EPROGMISMATCH`, `EPROGUNAVAIL`, and `ERPCMISMATCH`.
Their possible operation-specific treatment belongs in future typed wrappers.
Unknown positive values and all negative inputs also return -1.

The independent expected values in `tests/errno_cases.inc` cover 89 shared
symbolic names, including aliases. They come from the headers below.
Kernel-only native pseudo-errors are excluded from this userspace reference.

## Build and test

Use the selected SDK compiler, LLVM linker, native C target flags and runtime.
Build the module with `-std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared`,
`-fvisibility=hidden`, `-fno-emulated-tls`, and SONAME `libpvr_errno_abi.so`.
Compile `tests/errno_adapter.c` with the same native C flags and `-pthread`.
Link the consumer against that module and use a literal `$ORIGIN` runpath
or a process-local library directory. Run the consumer as an ordinary user.

The host diagnostic selects the Linux native ABI and the same SDK compiler.
Its instrumented variant adds `-fsanitize=address,undefined` and
`-fno-omit-frame-pointer` to the module and consumer.

On 2026-11-02 the normal and ASan/UBSan Linux x86_64 consumers passed all
476 checks. They cover translation, native errno preservation, unknown inputs,
explicit clearing, writable foreign storage and isolation between two threads.
A separate reference-header conformance consumer passed 89 comparisons.
Three isolated mutations returned the expected check-failure exit 65:

- Shared global storage instead of thread-local storage.
- Linux EAGAIN incorrectly encoded as 12.
- Conversion changing the foreign slot as a side effect.

Cppcheck and Clang Static Analyzer passed for the new module and consumer.
The AArch64 module and consumers cross-linked against the completed v2 C base.
The module has native ELF TLS and three namespaced function exports.
It defines no `errno`, `__errno`, or `__errno_location` alias.
Valgrind was unavailable in the selected prefix and was not run.

This module has not run on the target. Its native-only rejection cases are
compiled into the target consumer but have no target runtime result yet.
The tests link the adapter as a normal dependency; late loading, unloading,
vendor constructors, signal handlers, cancellation and complete vendor ABI compatibility remain
outside this result. Kernel, firmware, GPU and display state were not accessed.

## Pinned references

- BSP [errno-base.h](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/include/uapi/asm-generic/errno-base.h)
  and [errno.h](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/include/uapi/asm-generic/errno.h).
- AArch64 [UAPI export list](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/arch/arm64/include/uapi/asm/Kbuild)
  and [generic export list](https://github.com/CrealityTech/sonic_pad_os/blob/7f37a7fbf4ad59907034715e3d967b9177de1cd4/lichee/linux-4.9/include/uapi/asm-generic/Kbuild.asm).
- EmberBSD [native errno definitions](https://github.com/oxtech-ember/EmberBSD/blob/a249cbf317cf05eee4dfa06201098022ccc498ef/sys/sys/errno.h).
  The checked target base supplied the preprocessed userspace names.
- musl v1.1.24 [accessor declaration](https://github.com/ifduyue/musl/blob/v1.1.24/include/errno.h)
  and [generic error aliases](https://github.com/ifduyue/musl/blob/v1.1.24/arch/generic/bits/errno.h).
  These are interface references, not a claim about the vendor bundle's exact
  musl release.
