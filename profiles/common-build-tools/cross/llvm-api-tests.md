# Shared LLVM C API and ORC acceptance

These consumers test the installed common LLVM package on EmberBSD/AArch64.
Current probes select 23.1.3; the earlier 23.1.2 runtime receipt remains historical.
They do not install another runtime or build LLVM. Cross compilation requires
the accepted GCC16 cross tools, the target sysroot with LLVM's dependencies,
and the [host metadata tool](../../common-graphics/cross/llvm-config.md)
prepared against that sysroot and the completed target LLVM stage. Its prefix
may be the package stage's `/usr/pkg` directory or the installed sysroot's
`/usr/pkg`. The library must match the metadata receipt in either case.

```sh
ruby build-llvm-api-tests.rb /absolute/cross-tools /absolute/target-sysroot \
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
It requires AArch64 NetBSD, LLVM's `isa<ObjectLinkingLayer>` and a C++
`dynamic_cast` across the shared LLVM ABI. Each of four lifecycles creates a
JIT, checks a typed missing-symbol error, compiles and calls a function on three
inputs, removes its resource tracker, checks the symbol is gone, and disposes
the JIT. The separate `--missing-symbol` run must exit 1 with `SymbolsNotFound`;
a timeout, signal or different error does not count as this expected failure.

A successful build proves API/link compatibility. Runtime acceptance requires
the actual target logs. These focused checks do not establish Mesa rendering,
Vulkan, other CPU backends or the complete upstream LLVM test suite.
