# Common protobuf for KiCad

This probe prepares protobuf 36.2 and the common Abseil 20260817.0 provider.
It builds matching native `protoc` and AArch64 libraries with GCC 16.2.0.
The target installs under `/usr/pkg` in a private stage.
It uses external Abseil and the common target GCC runtime.
Upstream's utf8_range and static UPB components remain part of protobuf.

The official latest-release endpoints still select these versions on 2026-10-18:

- [protobuf v36.2](https://github.com/protocolbuffers/protobuf/releases/tag/v36.2), BSD 3-Clause.
- [Abseil 20260817.0](https://github.com/abseil/abseil-cpp/releases/tag/20260817.0), Apache 2.0.

`sources.sha256` pins the official release assets, including their exact filenames.
The preparer checks both archive hashes before extraction.
It applies canonical pkgsrc portability patches with zero fuzz.
It then applies the local correctness fixes.
An identical patch already in the canonical recipe is applied only once.
The local files identify AI assistance and their upstream submission status.

## Build

Provide CMake, Ninja, curl, patch, tar, sha256sum and GNU realpath on `PATH`.
Set these variables to absolute paths:

| Variable | Meaning |
| --- | --- |
| `PROTOBUF_WORK` | Dedicated source, build and output directory |
| `PKGSRC_BASE` | Canonical pkgsrc source root with EmberBSD overlays |
| `NATIVE_CC`, `NATIVE_CXX` | Native GCC 16.2.0 compiler commands |
| `NATIVE_ZLIB_PREFIX` | Common native shared zlib 1.3.2 provider |
| `CROSS_PREFIX` | GCC16 cross prefix ending in `aarch64--netbsd-` |
| `EMBERBSD_SYSROOT` | Coherent EmberBSD base/comp sysroot |
| `EMBERBSD_GCC_RUNTIME` | Common target `/usr/pkg/gcc16` prefix |
| `PROTOBUF_STAGE` | Optional target stage inside `PROTOBUF_WORK` |
| `JOBS` | Build parallelism; default 2 |

Prepare sources before building. Preparation does not need a compiler:

```sh
./build.sh prepare
./build.sh native
./build.sh target
./build.sh contracts
```

`./build.sh all` runs those steps in order.
Use `native-contracts` or `target-contracts` to build only those consumers.
Use `target-abseil` and then `target-protobuf` to build the target dependencies
in separate phases. The latter phase requires the target zlib provider first.
The target SDK must contain shared zlib 1.3.2 under `/usr/pkg`. The helper checks
its header version, ELF64 little-endian AArch64 shared-object identity and
`libz.so.1` SONAME, then records the header/library hashes in the private stage.
It passes both paths explicitly to CMake.
An existing stage rejects a changed zlib provider.
The native-only mode does not need a target sysroot or cross compiler.
Native GCC headers, linker files and runtime libraries must be available.
The native library retains gzip-stream support and selects the explicit zlib provider.
Use the host's configured `LIBRARY_PATH` and `LD_LIBRARY_PATH` if GCC is relocated.
The cross steps remove host include and library search variables.
The target linker flags retain `/usr/pkg/gcc16/lib` even when upstream install
rules set a target's `INSTALL_RPATH` to an `$ORIGIN` path.
Compilation databases remain in the individual build directories.

The helper requires GCC 16.2.0 and the `aarch64--netbsd` target triplet.
It rejects unmarked existing source directories and changed source inputs.
It rejects target stages outside the work directory, including symlink escapes.
An existing stage must match its source, libc and C++ runtime provenance marker.
It does not install files into the supplied sysroot or shared GCC prefix.

## Installed contracts

Install the target payload, then run both programs on EmberBSD:

```sh
/usr/pkg/libexec/emberbsd-tests/emberbsd-protobuf-contract
/usr/pkg/libexec/emberbsd-tests/emberbsd-upb-oom-contract
```

The C++ contract has fourteen checks using independent known protobuf wire bytes.
It checks decoding, unknown-field preservation and state reset.
It also writes and reads those known bytes through the installed gzip-stream API.
It rejects truncated fields, incomplete varints and invalid UTF-8.
The invalid UTF-8 case intentionally emits a protobuf diagnostic.

The C contract uses the installed UPB headers and library.
It exhausts a valid arena backed by a deliberately failing allocator.
Cloning must return `NULL`, preserve the source, and permit a later successful clone.
This exercises the actual allocation-failure path without replacing UPB functions.
The `--array-oom` mode lets the message allocation succeed and rejects the next
array allocation. Cloning must report failure instead of losing the repeated field.
The `--string-oom` and `--string-copy-oom` modes reject the scalar string
allocation after the destination message fits. They require `DeepClone` to
return `NULL` and `DeepCopy` to return `false`.
The default invocation checks all four allocation failures.
Failed `DeepCopy` can leave a partial destination, as before this repair.
The contract requires an intact source and correct failure status, not rollback.

## Local fixes and causal checks

The POSIX `protoc` patch calls `ShutdownProtobufLibrary()` after `ProtobufMain`
returns and destroys its local CLI and generator objects.
This follows the lifetime contract documented in upstream `message_lite.h`.
It returns the original CLI result.
Compare native 36.2 generators before and after that patch:

```sh
./check-protoc-output.sh /path/to/baseline/protoc /path/to/patched/protoc \
  /new/private/protoc-output
```

This checks generated C++ bytes and unknown-option error behavior.
It does not prove memory cleanup. Use the separate memory gate below.

The UPB patch checks the `upb_Message_New` result before copying a message.
Its failure result matches the existing `upb_Message_DeepClone` contract.
The repeated-field patch also propagates a failed `upb_Array_DeepClone` result.
The scalar-string patch checks allocation before copying bytes and propagates
failure through both public copy APIs. No public ABI changes.
Build the native causal controls after the patched native installation:

```sh
./build-native-baseline.sh
```

This helper uses GCC 16.2.0 and the verified release archive.
It builds the original UPB through a separate upstream CMake graph.
It applies only the two canonical build/header portability patches.
The control has debug information for allocation-failure stack traces.
The original CLI entry point links to the same installed compiler libraries
as the patched CLI. The helper refuses to overwrite an existing control tree.
Keep the generated command databases, source hashes and binaries.
Then run this causal check on a Memcheck-supported native host:

```sh
./check-upb-oom.sh /path/to/baseline/consumer /path/to/patched/consumer \
  /new/private/upb-output
```

The baseline must fail with an invalid write in `_upb_Message_Copy`.
Its separate array case must expose false success with a missing repeated field.
Both scalar string cases must fail with an invalid write in the string helper.
The patched consumer must pass strict Memcheck with no suppressions.
Both complete logs remain in the output directory.

Use the same strict options for native code generation and the C++ consumer:

```sh
valgrind --tool=memcheck --track-origins=yes --leak-check=full \
  --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
  "$PROTOBUF_WORK/build-native-contract/emberbsd-protobuf-contract"
```

Retain unsuppressed diagnostics and classify them against the current binaries.
[MEMORY.md](MEMORY.md) documents the current process-lifetime exceptions and
their source ownership. None came from the previous environment's unavailable
logs. The raw CLI and C++ consumer runs fail the strict all-leak-kinds gate.
Run this separate gate after recording the raw results:

```sh
./check-protoc-memory.sh \
  "$PROTOBUF_WORK/causal-control/protoc-build/protoc-baseline" \
  "$PROTOBUF_WORK/native/bin/protoc" \
  "$PROTOBUF_WORK/build-native-contract/emberbsd-protobuf-contract" \
  /new/private/protoc-memory-output
```

Both CLI variants use the same exact exception set. The original variant must
retain descriptor-pool errors, and the repaired variant must have none.
The UPB check uses no exceptions.

## Current validation boundary

The files were reconstructed after an environment reset.
Previous binaries, logs and exact Memcheck suppression stacks were unavailable.
Their former results are not new evidence for these reconstructed files.

On 2026-10-18, the official release versions and archive SHA256 values were checked.
Source preparation, zero-fuzz patch application and repeat preparation passed.
Shell syntax and patch reversal against the official source passed.
The native GCC16 build and matching installation passed. Both consumers passed:
14 C++ checks with gzip, and four UPB allocation-failure scenarios.
All UPB scenarios passed strict Memcheck without exceptions. The original
library reproduces the invalid writes and repeated-field false success.
The CLI controls emit identical generated bytes and retain the same error status.
The repaired CLI and C++ consumer pass with the documented process-lifetime
exceptions; the original CLI still fails with 96 unsuppressed contexts.
[ANALYSIS.md](ANALYSIS.md) records source-analysis findings and limitations.
The GCC16 AArch64 build and full private installation now pass for Abseil,
protobuf and both installed consumers. The final 105 ELF files have the target
architecture; all 102 C++ outputs retain the common GCC16 runtime path.
The versioned shared-library closure and both contracts also run in the
verified AArch64 E34 guest with the registered GCC16 runtime and zlib packages.
All fourteen C++ checks and all four UPB allocation-failure modes pass without
loader overrides. Loaded provider hashes match the accepted stage and SDK.
The guest receives no generator, headers or static libraries for this check.

This stage is a CMake probe payload. It is not a registered pkgsrc provider.
The separate [canonical packages](../../../profiles/common-build-tools/cross/protobuf.md)
now carry the same fixes. Their complete builds, disjoint runtime/SDK partition,
all 353 installed SDK entries and two GCC16 consumer links pass.
The ordinary runtime package also passes both contracts in the AArch64 VM,
full payload verification and normal removal/reinstallation. Its 341 SDK
entries remain absent from the guest. The [actual KiCad API contract](../application/tests/api/README.md)
passes native and target compilation and execution with unchanged generated
bytes. Full KiCad acceptance remains pending.
