# Linux AArch64 hardware UMD diagnostic

This diagnostic builds the upstream hardware UMD at commit
`f35bac0513a7757f8ba6d314d93063214da89c28` with native GCC 16.2.0 on a
GitHub AArch64 runner. This historical source is selected for its Linux
KMD interface, not as a replacement for the canonical 6.1.1 NetBSD source
probe. The upstream environment names its UMD **6.0.0**. A KMD version
does not determine the UMD library version.

The original archive is Apache-2.0 UMD source, with its original header
and third-party notices. `include/kmd/armchina_aipu.h` is an upstream
relative symlink to the KMD UAPI header. Extraction preserves that link
only inside the source tree. The resolved header SHA256 is checked.

```sh
python3 probes/compass-umd/linux-candidate.py \
  --work /absolute/new-work --output /absolute/new-artifact
```

Only native Linux/AArch64 and GCC 16.2.0 are accepted. The hardware
`standard_api`, `aipu_v3` choice compiles all 24 upstream translation
units. It does not select `SIMULATION` or the Python API. No simulator,
model compiler, vendor SDK, ONNX package or external ELFIO library is used.
The original warning policy remains enabled. The recipe creates build
directories before parallel compilation because the upstream make graph
does not order those dependencies.

The Linux-only `0004` patch removes the unused `super_graph.h` include from
`context.cpp`. GCC16 rejects that unfinished upstream class for hidden
virtual overloads. The recipe requires the original context to reproduce
that diagnostic, then requires the patched context to pass the same syntax
check. Both source hashes are checked. No graph implementation or UAPI is
changed. Cppcheck compares the pristine and patched include paths and
rejects introduced diagnostics.

The DSO uses `-static-libstdc++ -static-libgcc`, `-z defs`, and hidden static
archive symbols. ELF checks reject shared GCC runtime dependencies,
GLIBCXX/CXXABI/GCC symbol version requirements and RPATH/RUNPATH. They record
all glibc symbol requirements and reject requirements newer than glibc 2.43.
This is an explicit diagnostic compatibility bound, not an executed check
on every earlier libc release. GCC license texts, the Runtime Library
Exception, source URL and static archive hashes accompany the artifact.

The no-device consumer loads the exact private DSO with immediate symbol
binding. It requires `/dev/aipu` to be absent, checks actual public API
failure returns over four cycles and compares descriptor counts. It checks
every resolved public symbol's provider and inventories loaded libraries.
The genuine vDSO is identified by `AT_SYSINFO_EHDR`, rather than its name.
A real foreign DSO with a vDSO-like basename must fail this inventory.
glibc's error-path `backtrace` can load one system `libgcc_s` unwinder; that
does not introduce a GCC16 runtime requirement into the diagnostic DSO.

Valgrind checks these real failure paths with leak and uninitialized-value
diagnostics enabled and nonzero error exits. Cppcheck uses the actual
compiler commands, GCC system include paths and selected target builtins.
It does not model all GCC intrinsics. Unchanged upstream findings are
retained in the artifact; a completed analysis is not a clean-analysis
claim. No Clang or GCC C++ path analyzer result is claimed.

The artifact contains source hashes, original source, full build commands,
compiler dependencies, static runtime inputs, ELF dependencies and analysis
logs. It is a Linux diagnostic, not an installed EmberBSD package, a native
kernel transport, a certification or evidence of physical NPU execution.
No model is included. Device initialization, memory mapping, scheduling,
finite job completion, numeric golden comparisons and repeated inference
require a separate accepted hardware scenario.
