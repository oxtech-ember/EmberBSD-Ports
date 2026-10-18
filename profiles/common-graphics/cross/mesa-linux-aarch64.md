# Mesa 26 acceptance on Linux → EmberBSD/AArch64

Linux amd64 with GCC16.2.0 cross-built the complete selected MesaLib
26.2.4nb9 package on 2026-10-18. The installed package passes CPU rendering
and all 39 target test invocations in the E34 AArch64 VM. The VM uses
EmberBSD kernel and userspace with the NetBSD 11 ABI. It has no procfs.

## Inputs and package gates

Use the [complete graphics composition](profile.md) with the common GCC16
toolchain, Python 3.15, Meson 1.12.1, Wayland 1.26.0, protocols 1.49 and
the accepted [LLVM 23.1.3 runtime/SDK](../../common-build-tools/cross/llvm-linux-aarch64.md).
The native sealed `llvm-config` reads that target installation. Native
LLVM generators and the target SDK stay on the build host. The VM receives
ordinary runtime/library packages, including their normal package data.
It receives no compiler, LLVM SDK, `llvm-config` or Wayland scanner.

The selected Gallium drivers are V3D, VirGL, softpipe, llvmpipe and Zink.
X11, Wayland, EGL, GBM, GL/GLES, shared LLVM ORC and upstream tests remain
enabled. The optional Vulkan ICD is off; Zink retains its Vulkan loader
dependency. LLVM retains all 25 backends. No test or selected feature was
removed to obtain this result.

The source recipe includes the native Flex selection in Ports `8aa9c79`
and the NetBSD executable-path repair in `890c306`. The common cross
configuration is pinned to `3d0e9751b0cfd64518effc4c7ef94104075b5bd0`.
The [Flex regression](../tests/mesa-native-flex.py) checks real dependency
routing and generates all six upstream lexers with native Flex.
The [process-path regression](../tests/mesa-process-path/README.md) covers
the real `KERN_PROC_PATHNAME` result and buffer boundaries without procfs.
The upstream function fails before the repair and passes after it in the VM.

| Artifact | SHA256 |
| --- | --- |
| Upstream `mesa-26.2.4.tar.xz` | `bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9` |
| `MesaLib-26.2.4nb9.tgz` | `9397e95b569ddf27c3c16a673c081e181937dfab849aa5e40ccb4afcd066026f` |
| Prepared target test bundle | `c626be965c44e26b588f771961eb183f01a362abfc15618b62df795d92580f2e` |
| Installed Mesa `+CONTENTS` | `c8cce19d191d1293736984fe30ea095599e7700c2472929e9829cbc54e79085a` |

Normal pkgsrc compilation, staging, PLIST, permission, PIE/RELRO, RPATH,
work-reference and package checks pass. Normal package installation in
the build-host target sysroot passes. Readback verifies all 97 payload
entries, their modes, exact symlinks and package registration.

Eight actual upstream host invocations pass: drirc DTD validation, NIR
algebraic parsing, EGL entrypoints and five target-ELF symbol checks.
They use the real Meson test metadata and explicit cross `nm`.

## Installed target result

Prepare and run the existing [package test workflow](mesa-package.md)
against the nb9 package and its matching source/build tree. The bundle
contains GCC16-built test executables and fixtures. Its runner verifies
installed files, exact links and 113 runtime library paths before execution.
It does not carry private replacement runtime libraries.

Surfaceless EGL reports EGL 1.5, OpenGL ES 3.2 and
`llvmpipe (LLVM 23.1.3, 128 bits)`. Four complete lifecycles reject an invalid
shader, clear a surface, render a triangle and compare pixel values.
The wrong expected renderer is rejected with exit 1.

All 39 upstream target invocations exit zero, including both process tests,
NIR, SPIR-V, seven llvmpipe JIT tests, VirGL staging, Zink formats and GBM ABI.
`Cache.List` is an upstream internal skip. Nine NIR cases remain disabled.
These outcomes are separate from the 39 successful invocation statuses.

Normal upgrade and an unchanged consumer linked against nb8 pass.
Normal package deletion removes all 97 payload paths and links. The real
consumer then fails in the loader because `libEGL.so.1` is absent.
Reinstalling the same hash-verified archive restores the exact payload,
library closure, inventory, four render lifecycles and both process tests.
`pkg_admin check` verifies 9,956 files from 46 packages after reinstallation.

The [raw target logs](../tests/mesa-linux-aarch64/README.md) preserve these
results. Their expected negative checks include explicit failure messages.

## Analysis and memory scope

Actual selected Mesa translation units use the real target compile database
and sysroot for GCC16 `-fanalyzer`, Clang 19 Static Analyzer and Cppcheck 2.22.
Clang only analyzes code; GCC16 produces every native and target executable.
GCC and Clang report no diagnostics in the reviewed units. Cppcheck retains
the same upstream findings before and after patching: signed-shift and
inline-assembly modeling limitations, expanded macros and style/unused code.
This is focused analysis, not a clean whole-Mesa claim.

The real-source V3D cache lifecycle fixture passes ASan/UBSan, allocation
failures and five rejected mutations in both simulator configurations.
Strict native Memcheck reports zero errors, live blocks or suppressions.
The process-path host contract also passes sanitizers and strict Memcheck.
These fixtures do not exercise physical V3D hardware.

The native Flex generator's strict Memcheck run reports existing tool
allocation leaks. That finding belongs to `devel/flex`; no Flex C source
changed here. Functional generation passes, but Flex is not claimed memory
clean. The generator logs retain the findings without suppressions.

Valgrind does not support the selected NetBSD/AArch64 target. A GCC16
UBSan-trap render consumer passes in the VM. It instruments the consumer
and header code, not Mesa/LLVM DSOs or generated JIT code.

Physical GPU execution, X11/Wayland presentation, HDMI, Qt and KiCad remain
separate acceptance work. This result establishes installed CPU rendering
on the Linux/E34 cross stack. Earlier CM5 and Zero 3W receipts retain their
own package, driver and hardware scope. Upstream licenses and authorship
remain in the source and normal packages.
