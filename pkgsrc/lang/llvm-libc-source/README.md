# Shared LLVM libc source

This source-only package prepares the common LLVM runtime source with
`lang/compiler-rt/files/runtime.py` and installs its `libc` component at
`${PREFIX}/share/llvm-libc-source`. The only LLVM version, archive and patches
remain with the existing LLVM and compiler-rt owners. The upstream `LICENSE.TXT`
and all component source files are retained. This source is for consumers
such as V8; it does not replace EmberBSD libc or enter the target sysroot.

The ordinary pkgsrc build needs the selected SDK source code in
`EMBERBSD_SDK_SOURCE` and the selected host tool prefix in
`EMBERBSD_LLVM_LIBC_HOST_PREFIX` (default `TOOLBASE`). A pre-existing full
prepared runtime source may also be used through the existing `runtime.py`
producer: point the consumer at its `libc` subdirectory after checking the
version, archive, applicable patches and component bytes.

The installed component includes an SDK prepared-tree receipt. For a detached
payload check, run the selected host Python with
`files/verify-payload.py --sdk-source "$SDK_SOURCE" --source "$SOURCE"`.
The receipt records the archive and runtime recipe inputs as provenance; this
check verifies the bytes and does not treat unrelated recipe changes as a new
compiler or SDK admission requirement. The package preparation itself uses
all current common runtime patches with zero fuzz through the existing owner.
