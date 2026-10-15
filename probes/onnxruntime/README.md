# ONNX Runtime installed CPU inference API

The [canonical ONNX Runtime 1.31.0 package](../../pkgsrc/local-ai/onnxruntime)
provides a shared C API and the upstream C++ wrappers. The CPU execution
provider uses standard ONNX operators and baseline AArch64 NEON.
See [provenance](PROVENANCE.md), [validation](VALIDATION.md),
[source pins](sources.tsv) and [internal dependency pins](dependencies.tsv).

The profile uses GCC 16.2.0, C++20 and the common Eigen 5.0.1 headers.
Training, Python bindings, contrib operators, traditional ML operators,
telemetry, cpuinfo, XNNPACK, KleidiAI, SVE and GPU/NPU providers are disabled.
It is not a reduced-operator or minimal ONNX build. Upstream Python code
generators are a build dependency. No EmberBSD helper uses Python.

## Cross build

The source helper below uses a Linux x86-64 build host.
Use the coherent EmberBSD AArch64 sysroot and GCC16 runtime. The compiler,
libc, headers and runtime must come from the same accepted fork build.
Install the common Eigen provider into a writable copy of that sysroot.
The build verifies every archive and applies the canonical patches without
fuzz. It records the actual CMake cache and compilation database.

```sh
sh probes/onnxruntime/fetch.sh /absolute/archive-cache
JOBS=2 sh probes/onnxruntime/build-runtime.sh cross /absolute/gcc-prefix \
  /absolute/emberbsd-sysroot /absolute/archive-cache /absolute/new-cross-work
```

The staged installation is `NEW_CROSS_WORK/stage/usr/pkg`. It contains the
runtime's shared libraries, public headers, CMake exports, pkg-config file
and original notices. Internal dependency sources are linked privately.
Their Abseil, protobuf and FlatBuffers SDKs are not installed as competing
public providers. Eigen remains the common separately owned package.

Protobuf's compiler runs on the build host. The Linux x86-64 cross helper obtains
the upstream-pinned protobuf 33.6 host executable and verifies its archive.
Native NetBSD builds compile that tool from the same pinned protobuf source.
For pkgsrc cross builds, set `ONNXRUNTIME_NATIVE_PROTOC` to a matching native
`protoc`. Do not run a target AArch64 executable on the Linux build host.

## Native package and installed consumers

Export the pinned pkgsrc base with the common GCC16 development profile:

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc development-toolchain
```

The [toolchain profile](../../profiles/development-toolchain/README.md)
supplies the current GCC 16.2.0 recipe and its prerequisites. The exporter
automatically includes `local-ai/onnxruntime`; no separate package manager
or private source repository is needed. Its recipe declares GCC16, CMake,
upstream Python generators, GNU patch and the common Eigen provider.
The runtime does not require Python at execution time.

Installed consumers use `find_package(onnxruntime 1.31.0 EXACT CONFIG REQUIRED)`
or `pkg-config libonnxruntime`. The installed file is `libonnxruntime.pc`;
its internal `Name: onnxruntime` field does not change the module filename.
C applications include `onnxruntime_c_api.h`;
C++ applications include `onnxruntime_cxx_api.h`. Build against the installed
headers and shared library. The build tree is not a supported application SDK.
The standalone [C/C++ CPU example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/onnx-cpu)
uses these interfaces with a small independently generated ONNX graph.

The [AI/audio source profile](../ai-engines/README.md) uses this same version,
feature file and patches for its ORT and Silero consumers. Its older native
1.30.0 record remains historical evidence and is not a 1.31.0 acceptance claim.

The installed contracts build independently from the runtime build tree:

```sh
cmake -S probes/onnxruntime/tests -B /absolute/new-contract-build \
  -Donnxruntime_DIR=/usr/pkg/lib/cmake/onnxruntime
cmake --build /absolute/new-contract-build
ctest --test-dir /absolute/new-contract-build --output-on-failure
```

Set `ONNX_TEST_DATA` to a directory with `silero_vad.onnx` and `test.wav`
to include the existing Silero compatibility contract. Obtain these unchanged
files from [the pinned model archive](model-sources.tsv) and verify their
[asset hashes](../ai-engines/models.tsv). Preserve its original MIT license.
The model is separate from the runtime package.

CPU inference does not establish model accuracy, real-time performance,
physical-board support or accelerator operation. The validation record
states the exact model contracts, analysis coverage and platform boundaries.

## Constructor compilation regression

The full source control requires Ruby, the configured cross-build directory,
the unmodified pinned runtime source and the same compiler/sysroot. It uses
the actual production compilation database and canonical patch. It requires
the original GCC16 constructor diagnostic and a successful patched compile.

```sh
ruby probes/onnxruntime/check-selector-registry.rb \
  /absolute/cross-work/build/compile_commands.json \
  /absolute/unmodified-onnxruntime-1.31.0 /absolute/new-regression-results
```

The helper preserves the source tree and all original warning flags. It
checks that the public class declaration remains unchanged. This verifies
construction and compilation; it does not execute MatMulNBits inference.

## Target acceptance driver

`run-target.sh PACKAGES TESTS NEW_RESULTS` runs on AArch64 EmberBSD with
pkgtools and the coherent GCC16 runtime already present. It requires a fresh
results directory and no installed ONNX Runtime package. It installs the
actual `onnxruntime-1.31.0.tgz`, checks inference and errors, removes the
package, reinstalls it and compares the results. Preserve its output.

Install the example's C and C++ programs under `/usr/pkg/bin` first. Their
`$ORIGIN/../lib` path must refer to the installed runtime. `ONNX_APP_PREFIX`
can select another application prefix. Do not move these installed programs
to an unrelated test directory without preserving their library layout.

Prepare `TESTS` from the public sources and the same compiler/sysroot:

| Inputs | Source |
| --- | --- |
| `check-onnx-csv`, `onnx-thread-lifecycle`, `models/tiny-mlp.onnx`, `models/malformed.onnx` | The Examples `ai/onnx-cpu` build |
| `onnx-pkgconfig-c` | The complete example `inference.c`, compiled with `pkg-config libonnxruntime` |
| `onnx-contract`, `onnx-affinity-contract`, `silero-contract` | The installed [contract build](tests/CMakeLists.txt) |
| `posix-thread-baseline`, `posix-thread-patched` | The [actual-source POSIX controls](tests/posix-thread/README.md) |
| `onnx-header-reason-c`, `onnx-header-reason-cxx` | The [installed header controls](tests/header-reason/README.md) |
| `onnx-header-reason-cxx-baseline` | The same C++ ABI source compiled with pristine pinned headers |
| `onnx-upstream-controls` | The [selected unchanged upstream tests](tests/upstream/README.md) |
| `float16-baseline`, `netbsd-cpu-source-contract` | The existing AI-engine source controls, with pristine BFloat16 and patched NetBSD CPU headers |
| `silero/silero_vad.onnx`, `silero/test.wav` | The verified optional MIT fixture described above |

Give test-only target programs an explicit `/usr/pkg/lib` and GCC16 runtime
search path when copying them out of their build directories. Keep the
independent CSV checker free of an ONNX Runtime dependency. The driver checks
the real loaded libraries before inference and rejects build-host paths.
