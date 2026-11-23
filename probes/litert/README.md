# LiteRT CPU source profile

LiteRT 2.2.0 runs `.tflite` models through its C API and C++ wrappers.
This profile cross-builds a shared CPU runtime and the companion
[LiteRT-LM 0.18.0 engine](../litert-lm/) for EmberBSD/NetBSD 11 AArch64.
It belongs to [EmberBSD](https://github.com/oxtech-ember/EmberBSD).

The source profile passes installed C/C++ and Engine contracts on a physical
NetBSD 11/AArch64 A733 board. See [validation and model identity](VALIDATION.md).
TinyLlama-1.1B generates matching text and token IDs in two independent CPU
sessions after explicit metadata preparation, using a disk-backed weight cache.
It is not a pkgsrc package or a binary release.
GPU, NPU, experimental tensor DSL, Java and Python bindings are excluded.
The LM engine supports SentencePiece models; Rust Conversation APIs and
Hugging Face tokenizers are not built by this profile.

## Build on the development host

Use the [GCC 16 cross toolchain](../../profiles/development-toolchain/cross/)
with a matching NetBSD/AArch64 sysroot containing the GCC 16 target runtime.
CMake 3.25 or newer, Ninja, a host C/C++ compiler, curl, tar, patch and
SHA256 tools are needed. Preserve the sysroot's base-library SONAME files and
symlinks, including libm, libpthread and libz; linker-name files alone are
insufficient for a consumer of the shared runtime. When creating a target
archive on macOS, use `COPYFILE_DISABLE=1 tar --no-xattrs --no-acls --no-fflags`
to avoid errors restoring Apple metadata on NetBSD.
Install the source-only `devel/ml-dtypes` package in the selected sysroot. To use its native package or a tree prepared by the common source producer, set `EMBER_ML_DTYPES_SOURCE` to that source directory. The same tree can be used for offline builds.

XNNPACK's upstream microkernel list generator uses host Python; the installed
runtime does not require Python. Project-owned helpers use shell, C and C++.

```sh
export EMBER_CROSS_PREFIX=/path/to/toolchain/bin/aarch64--netbsd-
export EMBER_SYSROOT=/path/to/sysroot
JOBS=8 sh build.sh /absolute/path/to/litert-work
```

`JOBS` defaults to the host CPU count. Host `flatc` and `protoc` are built
separately from target code. All archive versions and SHA256 values are
pinned; CMake dependency downloads are disabled. A second argument may name
a previously populated archive directory. Completed work directories can
be resumed; use a new work directory after changing source patches.

Target files are staged under `WORK/stage/usr/pkg`. Transfer the stage to an
isolated prefix on the test target before a system installation. The target
needs the matching `/usr/pkg/gcc16` runtime and the base zlib library.

## Check the installed files

On the build host, compile independent consumers against the staged SDK:

```sh
cmake -S tests/installed -B /absolute/path/to/consumer-build -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/netbsd-aarch64.cmake" \
  -DEmberLiteRt_DIR=/absolute/path/to/litert-work/stage/usr/pkg/lib/cmake/EmberLiteRt
cmake --build /absolute/path/to/consumer-build
```

Copy `stage/usr/pkg` to a private target prefix, preserving its directory
layout. Put the two `installed-litert-*` executables in that prefix's `bin`.
On the target, run the repository's script and both independent consumers:

```sh
sh probes/litert/test.sh /path/to/prefix
/path/to/prefix/bin/installed-litert-c /path/to/prefix/share/ember-litert/runtime-add.tflite
/path/to/prefix/bin/installed-litert-cpp /path/to/prefix/share/ember-litert/runtime-add.tflite
```

The checks cover repeated numerical inference, invalid inputs, recovery,
standalone C++ headers and relative shared-library lookup. No `LD_LIBRARY_PATH`
override is needed. See [the runtime contract](tests/runtime-README.md).

For language-model checks, pass the verified LiteRT-LM source directory as
the second argument to `test.sh`; only `runtime/testdata/test_lm.litertlm`
is needed on the target. A third argument selects a trained model. Optional
downloads use pinned revisions and checksums from [models.tsv](models.tsv):

```sh
sh probes/litert/fetch-model.sh tinyllama /absolute/path/to/original.task
sh probes/litert/prepare-model.sh tinyllama /absolute/path/to/litert-work \
  /absolute/path/to/original.task /absolute/path/to/tinyllama.task
# On the target, after transferring the prepared model:
mkdir -p /path/to/packed-weights
EMBER_LITERT_CACHE_DIR=/path/to/packed-weights sh probes/litert/test.sh \
  /path/to/prefix /path/to/LiteRT-LM-0.18.0 /path/to/tinyllama.task
```

The [TinyLlama-1.1B conversion](https://huggingface.co/litert-community/TinyLlama-1.1B-Chat-v1.0)
has a separate Apache-2.0 license. The helper downloads weights only after an explicit
invocation; the build does not fetch models. Consult the linked model cards
before choosing a model for an application.
Preparation requires host `zip` and `unzip`. It replaces legacy MediaPipe
metadata with the current protobuf schema, preserving weight and tokenizer
hashes. See [the conversion boundary](model-metadata/README.md).
The packed-weight cache is explicitly selected and can occupy gigabytes;
the caller owns its cleanup. Without it, this TinyLlama conversion exceeded
the tested board's 4 GiB RAM during initialization.

## API integration

The staged CMake package provides `EmberLiteRt::Runtime`:

```cmake
find_package(EmberLiteRt CONFIG REQUIRED)
target_link_libraries(my_device PRIVATE EmberLiteRt::Runtime)
```

C++ consumers use upstream's `LITERT_NO_ABSL` header mode, avoiding a second
installed Abseil SDK. The shared runtime contains the same pinned Abseil
implementation used throughout this build. Model conversion runs separately
on the development host; TensorFlow's Python package is not installed here.

## Boundaries

The NetBSD XNNPACK adapter dispatches only the guaranteed ARM64 NEON/FMA and
FP16 conversion instructions. FP16 arithmetic, DOT, I8MM, SVE and KleidiAI
are not enabled by this adapter. This is a conservative portable CPU profile,
not a claim to use every feature of a particular SoC.

The exact dependency choices, imported code and adaptations are described
in [PROVENANCE.md](PROVENANCE.md). Trained models have separate licenses and
are not bundled or downloaded automatically by the build.
