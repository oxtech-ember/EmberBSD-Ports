# Native CPU inference and audio probes

This source probe prepares **ONNX Runtime 1.31.0**, **ncnn 20260526**,
**RNNoise 0.2** and **Silero VAD 6.2.3** for EmberBSD/NetBSD AArch64.
It supplies installed C/C++ consumer checks, without Python application code,
external inference services or an accelerator dependency.

The current build uses the [canonical ONNX Runtime port](../onnxruntime/README.md)
and [canonical ncnn port](../ncnn/README.md), including their feature profiles
and patches. Their separate GCC16 cross packages pass installed CPU acceptance
in AArch64 QEMU. The combined native script has not been rerun after this update.
Historical native builds with
ONNX Runtime 1.30.0 passed all seven installed consumer contracts and the
optional two-CPU affinity checks. [NATIVE.md](NATIVE.md) retains that run's
exact versions, configuration, measurements and output hashes.
This remains an experimental source profile, not a binary package or a board
support claim.

## Sources and profile

The ONNX Runtime source pin is 1.31.0. The other
components retain the release metadata checked on 2026-10-07. The release
URLs, immutable revisions, licenses and local patches are described in
[PROVENANCE.md](PROVENANCE.md). [sources.tsv](sources.tsv) pins source archives;
[dependencies.tsv](dependencies.tsv) pins ONNX Runtime's internal build inputs.
[models.tsv](models.tsv) pins the Silero ONNX model and upstream audio fixture.
Sources and models are fetched from upstream; no binaries are stored here.

The ONNX Runtime profile builds a shared C/C++ library with its CPU execution
provider. Training, Python bindings, telemetry, contrib operators, traditional
ML operators, XNNPACK, KleidiAI and GPU/NPU providers are disabled. Standard
ONNX operators remain available. CPU feature detection via the unsupported
cpuinfo backend is disabled. AArch64 baseline NEON remains available;
optional acceleration is not established by these tests.

Eigen uses the project's common **5.0.1** release. A small build patch makes
ONNX Runtime's existing preinstalled-Eigen option honor `find_package(Eigen3)`.
The remaining internal sources follow ONNX Runtime's pinned dependency set;
they are linked into that library, not installed as competing application
libraries. The upstream third-party notices and downloaded source licenses
are preserved alongside the installation.

The RNNoise release needs an unchanged upstream ARM build fix; its author,
commit and patch hash are retained in the provenance record.

ncnn builds its installed C/C++ API with baseline CPU operators and POSIX
synchronization. Its operator loops are serial with OpenMP disabled.
Vulkan, runtime ISA dispatch, converters, Python bindings and examples are off.
RNNoise uses its
release's embedded weights, mono 48 kHz audio and 480-sample frames. Silero
uses the pinned standard ONNX model with 16 kHz PCM, 512-sample frames,
64 samples of preceding context and explicit recurrent state. Its inference
runs through the same ONNX Runtime library.

## Build and run

Requirements: native GCC 16.2.0 C/C++ compilers, CMake, Ninja, GNU make,
GNU patch, curl, pkg-config, and Python 3.10 or newer. ONNX Runtime's upstream
build generators require Python even though Python bindings are disabled.
No project-owned helper uses Python. Model training is not part of this build.

Use a fresh absolute work path without whitespace. The build rejects an
existing directory and defaults to `JOBS=1`. It installs only into that work
path and does not change packages, services or the running desktop. Use
4 GiB RAM and keep the default single build job on small machines. One
compiler reached about 2.6 GiB RSS. The measured work tree used 1.73 GiB,
including source archives; allow at least 4 GiB of free disk space for headroom.

```sh
export PATH=/usr/pkg/gcc16/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export CC=/usr/pkg/gcc16/bin/gcc CXX=/usr/pkg/gcc16/bin/g++
work=/var/tmp/ember-ai-engines
sh probes/ai-engines/build.sh "$work"
sh probes/ai-engines/test.sh "$work"
```

`PYTHON=python3` and `PATCH=gpatch` are the defaults. Override these for the
installed tool names. An optional second build argument names a source cache
containing every archive in both manifests. Prepare it on another host with:

```sh
sh probes/ai-engines/fetch.sh /absolute/source-cache
```

Every archive is verified before extraction. Existing corrupt cache entries
cause an error; the fetcher never silently replaces them. ONNX Runtime's
upstream CMake verifies its own dependency hashes again. Stage logs, timing,
peak resident memory and installation data remain under `WORK/logs`.
A failed stage retains its exit status and prints its log tail.
The build also runs focused source-header contracts for BFloat16 conversion
and NetBSD's current-CPU query in the main thread and a worker.

## Installed contracts

`test.sh` uses installed CMake/pkg-config metadata, checks exact library
versions and verifies dynamic linkage to the private installation. The tests
are deliberately independent of the upstream build tree:

- ONNX Runtime: a small Add/Relu graph built from the ONNX wire format;
  exact expected values over 100 runs; malformed model, wrong shape and
  missing input-name rejection. Only the CPU provider may be registered.
- ncnn: the same arithmetic graph and values over 100 runs, plus a dense
  layer with known weights/biases; malformed graph and unknown input/output
  rejection. This checks an installed model consumer,
  not model conversion or all operator implementations.
- RNNoise: 144,000 deterministic PCM samples; equal output lengths, finite
  samples/probabilities, equivalent state across different frame batches,
  a quiet tail, incomplete-frame and non-finite input rejection.
- Silero: the upstream speech fixture between injected leading/trailing
  silence; speech detection, silence boundaries, state continuity under
  arbitrary incoming chunk lengths, correct final frame padding, and invalid
  sample-rate/PCM/model/WAV rejection.

Tests have deadlines. Silero's reported boundaries use a 0.5 frame threshold;
they are a software contract for this fixed fixture, not speech segmentation
accuracy or quality measurements. RNNoise's synthetic signal is not a speech
corpus. Microphones, real-time deadlines, echo cancellation, noise reduction
quality, battery use, other boards and accelerators need separate evidence.

Two additional affinity checks are opt-in. They require two available CPUs
and permission to change thread affinity. The ordinary build and seven CTest
contracts do not require that permission:

```sh
"$work/netbsd-cpu-source-contract" --affinity
LD_LIBRARY_PATH="$work/install/lib" "$work/test-build/onnx-affinity-contract"
```

The first confirms that NetBSD's reported CPU follows explicit worker
bindings. The second creates ORT sessions with two intra-op threads, queries
the kernel's actual worker masks, checks exact graph output and rejects
runtime error logs. Both probe available CPU IDs rather than treating the
online CPU count as an ID limit. Permission denial is reported as failure;
it is not converted into a successful acceptance result.
