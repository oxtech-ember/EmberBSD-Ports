# Source and adaptation provenance

The source inputs are Google AI Edge LiteRT 2.2.0 and LiteRT-LM 0.18.0.
Both retain Apache-2.0 licensing. Archive URLs and SHA256 values are in
[sources.tsv](sources.tsv) and [dependencies.tsv](dependencies.tsv).
Project-owned build helpers and tests use MIT; imported patches retain
upstream notices. This port was prepared with AI assistance; no upstream
acceptance is claimed.

The shared dependency set uses Abseil 20260817.0, FlatBuffers 25.12.19,
Protobuf 36.2, Eigen 5.0.1, SentencePiece 0.2.2, RE2 2025-11-05 and
nlohmann/json 3.12.0. TensorFlow 2.21.0 supplies the remaining LiteRT source
headers and a small set of converter/runtime implementation files; the full
TensorFlow runtime and Python package are not built. zlib 1.3.2 supplies
minizip sources only; compression uses the target's base zlib.

Internal XNNPACK, Ruy, gemmlowp, cpuinfo, FP16 and farmhash inputs
follow LiteRT 2.2.0's exact integration revisions. Their private interfaces
are part of that upstream runtime snapshot, not additional installed
system libraries. The ml_dtypes headers come from the shared `devel/ml-dtypes` source package or its prepared source tree. FXdiv is pinned to commit 63058eff77e11aa15bf531df5dd34395ec3017c8
instead of the upstream pthreadpool build's floating `master`. OouraFFT 1.0
is the upstream runtime's bundled FFT implementation; this does not install
a second FFTW or liquid-dsp package.

## EmberBSD adaptations

- `xnnpack-netbsd.patch`: allow NetBSD AArch64 and dispatch the architectural
  baseline without Linux-specific cpuinfo initialization. Optional ISA bits
  remain clear. The test compiles the actual upstream dispatcher.
- `ruy-netbsd.patch`: select Ruy's existing portable CPU tuning path on NetBSD;
  cpuinfo does not supply ARM ISA symbols on this OS. Optional ISA stays off.
- `litert-host-protoc.patch`: use the matching host generator during cross
  compilation; never execute a target `protoc` on the build host.
- `litert-cpu-cmake.patch`: honor disabled NPU support before fetching vendor
  SDKs and make experimental tensor examples optional.
- `litert-cxx-name-lookup.patch`: qualify C++ type names hidden by method names;
  strict GCC 16 consumers do not need `-fpermissive`.
- `litert-netbsd-link-map.patch`: include the NetBSD declaration used by the
  existing `dlinfo` diagnostics.
- `litert-no-absl-options.patch`: honor upstream standalone C++ header mode
  in runtime options without requiring an installed Abseil SDK.
- `regenerate-schemas.sh`: regenerate FlatBuffers headers from their upstream
  schemas with the selected generator. Version assertions remain enabled.

The [LM profile](../litert-lm/PROVENANCE.md) owns its API compatibility patches
and the exact GatedDeltaNet operator backport. Generated files, downloaded
sources, models and build products stay outside Git.
