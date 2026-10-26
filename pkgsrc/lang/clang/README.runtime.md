# Explicit EmberBSD target runtime selection

The NetBSD target driver honors an explicit `--rtlib` or `--unwindlib`
selection through LLVM's common `AddRunTimeLibs` policy. The EmberBSD SDK
selects the runtime family alongside its target, sysroot, and resource directory:

- LLVM uses `--rtlib=compiler-rt --unwindlib=libunwind -stdlib=libc++`.
- A declared GCC platform profile uses `--rtlib=libgcc --unwindlib=libgcc
  -stdlib=libstdc++` and that profile's matching GCC runtime directories.
- Bootstrap code that needs builtins without an unwinder uses
  `--rtlib=compiler-rt --unwindlib=none`.

The driver adds the selected runtime after libc, including static and shared
unwind selection. Static links group the C++, libc and runtime dependencies
so the linker can resolve references in both directions. Invalid and incompatible options use the common
Clang diagnostics. `-nostdlib`, `-nodefaultlibs`, and relocatable `-r` links
continue to omit default runtime libraries. `-nostartfiles` omits CRT files
while retaining the selected libraries. No automatic fallback occurs when a
selected runtime archive or library is missing.

The common recipe leaves Clang build-wide runtime defaults unset. With only
`--rtlib=compiler-rt`, NetBSD selects builtins without an unwinder. With only
`--rtlib=libgcc`, it selects libgcc and its unwinder. With only `--unwindlib`,
the unchanged NetBSD default runtime is libgcc: `libgcc` and `none` are valid,
while `libunwind` diagnoses the incompatible selection. SDK callers therefore
set both options.

An invocation without runtime flags retains the upstream NetBSD base ABI.
Native Darwin defaults are unchanged. `-stdlib` selects the C++ standard
library independently; choosing Clang does not establish a C++ ABI. Installed
native GCC configuration remains a separate legacy path until the complete
LLVM runtime producer can replace it.

The patch uses LLVM's shared runtime helper. FreeBSD and OpenBSD provide the
runtime ordering precedent, but their hardcoded base runtime names
are not suitable for EmberBSD's explicit SDK profiles:
[FreeBSD driver](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/clang/lib/Driver/ToolChains/FreeBSD.cpp),
[OpenBSD driver](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/clang/lib/Driver/ToolChains/OpenBSD.cpp),
[common runtime helper](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/clang/lib/Driver/ToolChains/CommonArgs.cpp).

`test/Driver/netbsd-runtime.c` is installed into the upstream test source by
the recipe patch. Run it with the matching configured Clang lit suite, alongside
`test/Driver/netbsd.c`, after building Clang. These tests inspect real driver
commands for AArch64 and amd64; they do not link or execute target code.
Actual LLVM runtime creation is documented in
[the common LLVM runtime producer](../llvm/README.runtime.md).
