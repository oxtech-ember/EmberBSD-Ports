# ONNX Runtime source and patch provenance

The official stable release **1.31.1**, published on **2026-10-26**, is pinned
at revision `6af1a932e2286d5c58166085d24c68783033edee`.
The [release](https://github.com/microsoft/onnxruntime/releases/tag/v1.31.1)
archive SHA256 is
`92ffbf8b97872fd1e73c9eebdf3319d9a3b24919ae438d27db903b72ee08939e`.
The primary source license is MIT, Microsoft Corporation and contributors.
The installed `ThirdPartyNotices.txt` preserves the upstream third-party
attribution. Original source copyright and SPDX identifiers are unchanged.
Historical patch-validation results below were obtained on 1.31.0; the
1.31.1 candidate has not yet completed build or target acceptance.

[sources.tsv](sources.tsv) pins the runtime archive.
[dependencies.tsv](dependencies.tsv) adds SHA256 checks to the selected
upstream `cmake/deps.txt` archives. Upstream CMake verifies their SHA1 pins
again when populating its local dependency mirror. Abseil and protobuf use
the common Ports providers; protobuf's native generator is a build tool.

| Internal source | Upstream pin | Principal license |
|---|---|---|
| date | 3.0.1 | MIT |
| FlatBuffers | 23.5.26 | Apache-2.0 |
| nlohmann JSON | 3.11.3 | MIT |
| Microsoft GSL | 4.2.1 | MIT |
| Boost mp11 | 1.82.0 | BSL-1.0 |
| ONNX | 1.22.0 | Apache-2.0 |
| RE2 | 2024-07-02 | BSD-3-Clause |
| SafeInt | 3.0.28 | MIT |

These are private source inputs for this runtime, not separate installed
application ABIs. This port does not claim that every internal upstream pin
is independently the latest release. Upstream dependency compatibility
patches remain in their original source paths. The installation copies
`LICENSE*`, `COPYING*` and `NOTICE*` files from the actual populated sources.
The standalone mp11 archive omits `LICENSE_1_0.txt`. Its original header
copyright notice and the unchanged Boost Software License 1.0 text are
installed explicitly. The same license is retained in `ThirdPartyNotices.txt`.
Eigen uses the separate common **5.0.1** provider, with its own MPL-2.0 notices.
Common Abseil and protobuf carry their licenses in their own packages.
Eigen template code is compiled into the runtime. Its current `COPYING*`
files and exact source pin are also installed under `licenses/onnxruntime/eigen5`.
These identify the current provider without changing the upstream notices.

## Existing model compatibility fixture

[model-sources.tsv](model-sources.tsv) pins the unchanged Silero VAD 6.2.3
archive for the existing AI/audio consumer regression. The model and WAV
hashes remain in the [original asset manifest](../ai-engines/models.tsv).
The original MIT license and Silero Team copyright accompany the fixture.
The model and recording are downloaded separately; they are not included
in the runtime package. This checks compatibility with the common runtime
upgrade. It does not add another inference engine or claim speech accuracy.

## Canonical local adaptations

The [package patch directory](../../pkgsrc/local-ai/onnxruntime/patches)
is the single current owner. Its patches are local, AI-assisted EmberBSD
adaptations. They have not been submitted or accepted upstream.
Patched files retain their original licenses. The POSIX `env.cc` and common
threadpool sources retain their TensorFlow Apache-2.0 notices and Microsoft
portions. The other patched sources retain their MIT notices. The added
NetBSD CPU helper is MIT.

- `patch-c-api-unknown-reason` replaces the C header's undefined signed shift
  with the defined signed minimum expression `(-2147483647 - 1)`. It preserves
  the existing C++ signed enum value, underlying `int`, size, alignment, and
  containing layout. The `uint32_t` API mask remains `0x80000000`. It does not
  change any API struct, function pointer, or API version. The strict C17 and
  C++20 [header controls](tests/header-reason) compare the installed interface.
- `patch-mlas-guard-pages` keeps the MLAS test guard pages inaccessible while
  declaring future read/write permissions with NetBSD `PROT_MPROTECT`.
  PaX otherwise rejects the later data-page commit. The POSIX allocation
  check uses `MAP_FAILED` and stops before `mprotect` on allocation failure.
  This changes only the upstream MLAS test header. It does not change the
  runtime library or disable guard pages, PaX, or any transpose test.
  The [guard controls](tests/mlas-guard) compare the real mapping calls and
  prove the allocation-failure path stops before protection changes.
- `patch-netbsd-affinity` uses NetBSD's allocated `cpuset_t` and
  `pthread_setaffinity_np`. It checks allocation, CPU IDs and operation errors,
  preserves error logging and destroys the CPU set.
- `patch-netbsd-thread-id` uses `_lwp_self()` for logging thread IDs.
  The public logging API and other platforms keep their existing behavior.
- `patch-netbsd-cpu-id` reads NetBSD's `_lwp_ctl()` communication area.
  Failure reports the existing unknown/error value, `-1`.
- `patch-installed-eigen` makes the upstream preinstalled-Eigen option
  select `find_package(Eigen3)`. It avoids another downloaded Eigen version.
- `patch-common-providers` selects the common Ports Abseil and protobuf CMake
  packages while retaining upstream's Abseil target list. Source fallback is
  disabled, and the matching native protobuf generator is selected explicitly.
- `patch-cpu-fused-helper` retains the existing CPU FP16 Conv activation
  helper when contrib operators are disabled. It does not register contrib
  operators. Strict final linking remains enabled.
- `patch-posix-thread-attributes` destroys initialized POSIX thread
  attributes after thread creation. It preserves the creation status and
  fixes the same owned-resource lifetime on success and failure paths.
- `patch-posix-thread-errors` reports the error value returned by the POSIX
  thread API. These functions return their error directly; reading unrelated
  `errno` could report the wrong cause for attribute or thread creation errors.
- `patch-static-selector-registry` constructs the MatMulNBits selector registry
  with a file-local free function. Calling a nonstatic member before base
  construction completes violates C++ construction rules, even when the
  factory does not read object state. The existing public const member
  delegates to the same factory. Its signature and the class layout remain
  unchanged. With the actual GCC16 AArch64 `-O2 -Werror` flags, the full
  translation unit reports `maybe-uninitialized` before the patch and
  compiles after it.
  This corrects a construction-phase defect.
  The selected profile disables contrib kernels; this compilation control
  does not claim runtime MatMulNBits numerical validation.

The earlier source profile's GCC12 single-pointer assignment and BFloat16
`isnan` adaptations are not applied to the GCC16/1.31.1 profile. The previous
1.31.0 check compiled the unchanged original BFloat16 source with GCC16 target headers. Older patches and numerical
measurements under `ai-engines` are historical artifacts. Current builders
consume the canonical package patches and feature file.

Original release code, local portability changes, installed API contracts,
native analysis and target VM execution have separate validation boundaries.
See [VALIDATION.md](VALIDATION.md) for the accepted evidence.
