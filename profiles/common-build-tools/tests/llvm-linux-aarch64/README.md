# Installed split LLVM: E34 AArch64 VM, 2026-10-18

Actual target output for the [Linux/GCC16 acceptance receipt](../../cross/llvm-linux-aarch64.md).

| Log | Execution |
| --- | --- |
| `api-first.log` | Ordinary cross-built C API/bitcode and default ORC JITLink/RTTI consumers, including typed missing-symbol rejection. |
| `runtime-lifecycle.log` | Normal runtime removal, real loader failure, exact reinstall, unchanged package inventory and renewed API/JIT execution. |
| `ubsan.log` | Separately built GCC16 UBSan-trap C/C++ consumers executing the same acceptance runner. |

The normal and instrumented invocations intentionally emit identical successful
test text. They execute different bundle hashes, recorded in the linked receipt.
UBSan covers consumer/header code; the shared LLVM DSO and generated JIT code
are uninstrumented. No target Valgrind, full upstream suite, Mesa rendering
or physical-board acceptance is claimed.
