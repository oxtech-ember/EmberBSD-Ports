# Shared LLVM C API and ORC acceptance

These consumers test the installed common LLVM package on EmberBSD/AArch64
or amd64. The builder selects the exact CPU from the checked metadata,
records it in the hashed bundle and uses the selected GCC16 startup objects.
The runner rejects a different target CPU.
Current probes select 23.1.4; the earlier runtime receipts remain historical.
They do not install another runtime or build LLVM. Cross compilation requires
the accepted GCC16 cross tools, the target sysroot with LLVM's dependencies,
and the [host metadata tool](../../common-graphics/cross/llvm-config.md)
prepared against that sysroot and the completed target LLVM stage. Its prefix
may be the package stage's `/usr/pkg` directory or the installed sysroot's
`/usr/pkg`. The library must match the metadata receipt in either case.

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
python3 -B build-llvm-api-tests.py /absolute/cross-tools /absolute/target-sysroot \
    /absolute/metadata-tool/bin/llvm-config /absolute/new-work
```

The builder uses real upstream `llvm-config` flags and shared linkage. It
checks the selected version, target, RTTI, library ELF header and SONAME,
records commands and input hashes, and rejects build paths in the consumers'
dynamic metadata. The archive contains the two executables, sources and runner.
It records the expected hash of the installed `/usr/pkg/lib` LLVM DSO.
Copy the archive to the target and verify its printed SHA256 before extraction.
The target must have this same package and its dependencies installed normally.

```sh
mkdir llvm-api-tests
tar -xzf llvm-api-tests.tar.gz -C llvm-api-tests
sh llvm-api-tests/run-llvm-api-tests.sh "$PWD/llvm-api-tests" \
    "$PWD/llvm-api-logs"
```

The runner verifies all bundle files and the installed shared LLVM before
`ldd` or execution. It rejects loader-path overrides. Each invocation has a
60-second limit through `/usr/bin/timeout`; `TIMEOUT` may select another
existing absolute timeout executable with the same interface. Keep the logs.

The C consumer builds and verifies IR, rejects a malformed module, serializes
bitcode, parses it into a new context, and compares the round-tripped IR.
The C++ consumer uses the default `LLJITBuilder` with no object-layer override.
It requires NetBSD with the CPU selected when compiling the test, LLVM's `isa<ObjectLinkingLayer>` and a C++
`dynamic_cast` across the shared LLVM ABI. Each of four lifecycles creates a
JIT, checks a typed missing-symbol error, compiles and calls a function on three
inputs, removes its resource tracker, checks the symbol is gone, and disposes
the JIT. The separate `--missing-symbol` run must exit 1 with `SymbolsNotFound`;
a timeout, signal or different error does not count as this expected failure.

A successful build proves API/link compatibility. Runtime acceptance requires
the actual target logs. These focused checks do not establish Mesa rendering,
Vulkan, other CPU backends or the complete upstream LLVM test suite.

## E34 VM: split LLVM 23.1.3 packages, 2026-10-18

The [Linux/GCC16 receipt](llvm-linux-aarch64.md) records ordinary runtime and
SDK builds, installed C API/bitcode and four default JITLink/RTTI lifecycles.
Normal runtime removal causes a real missing-DSO loader failure; reinstallation
restores the exact payload and passes the APIs again. UBSan trap instrumentation
also passes for both consumers; LLVM itself is uninstrumented. The guest
contains runtime libraries only. A sealed native helper agrees with all 16
query groups from the exact SDK tools run as temporary target QA fixtures.
This result does not establish the full upstream suite or Mesa rendering.

## CM5: LLVM 23.1.3, 2026-10-12

The complete cross package was upgraded normally on Compute Module 5 Rev 1
(BCM2712 D0, 4 GiB), running EmberBSD 11.0 `EMBERV3DRENDER #1`.
The prior verified package remains available for rollback. Matching
`py314-llvm-lit-23.1.3` was installed before LLVM; no forced dependency bypass
or loader override was used. The boot time was unchanged across acceptance.

Both C/C++ consumers now compare `LLVMGetVersion` with the actual generated
`llvm-config.h` macros. The earlier test still required patch version 2 and
correctly refused 23.1.3 before doing API work; that stale test expectation was
fixed without relaxing the exact header/runtime version check. Cppcheck 2.22
and GCC16 `-fanalyzer` report no diagnostics for the C consumer before/after,
using its real target preprocessing/compiler flags. This is not analysis of
the complete LLVM sources or a Valgrind run.

The installed C API test passes malformed-module rejection and bitcode/IR
roundtrip. All four default ORC JITLink/RTTI lifecycles pass; the separate
missing-symbol case exits 1 as required. Every dependency resolves through the
canonical installed runtime. All 16 host/target `llvm-config` query groups
agree. The sealed metadata helper passes 21 integrity/refusal checks.

| Artifact | SHA256 |
| --- | --- |
| `llvm-23.1.3.tgz` | `052b4a4e7afd291c21ee78f9c2cbd5e9c125164ff1faad44bbfb27d922793cfe` |
| `py314-llvm-lit-23.1.3.tgz` | `661a7609105b68f2e3c62f5b49172add02469ec2d9362654532c15a7e7ba3edf` |
| Installed `libLLVM.so.23.1` | `4570d91b080461fed8e3324b6f53bc8cbbe3fcdeee7982d481299c372bb9cdcd` |
| Corrected API test archive | `e859ab1df5f5eb8876f74079b702ee742114162c742b5b0ed2d4465c20f11f63` |
| Target metadata/runtime result archive | `d297878c2ee529718b2991e20e84b2c5bd224eda2adbdd934d13079d236e32f2` |
| Original metadata manifest anchor | `a48e32c7e040a2b6d199fc973837fdb21decbba597ea589289d626fe9f2bfe52` |

This renews the focused LLVM core acceptance. Installed Clang/LLD, the full
LLVM suite, Mesa consumers after this update, and a complete accelerated
Plasma session require their own results.
