# GCC16 cross build of whisper.cpp

Build whisper.cpp 1.9.5 CPU tools on Linux, then install and execute them on
EmberBSD AArch64. The [shared cross prerequisites](README.md#inputs) apply:
GCC/G++ 16.2.0, the fork-derived sysroot, matching GCC16 runtime libraries,
CMake, Ninja, patch, tar and checksum tools. Use fresh absolute output paths.
The native and cross recipes share `cpu.cmake` and `whisper-cpp/package.cmake`.

```sh
curl --fail --location --output /var/tmp/whisper.cpp-1.9.5.tar.gz \
  https://github.com/ggml-org/whisper.cpp/archive/d1be6fde11ac6e0407606b4e42fe72d34add8037.tar.gz
sh profiles/ai-cpu/cross/build-whisper.sh \
  /var/tmp/ember-cross /var/tmp/ember-sysroot \
  /var/tmp/whisper.cpp-1.9.5.tar.gz /var/tmp/whisper-cross
```

The helper verifies the archive and every canonical patch before extraction.
It builds three tools and four selected upstream tests. It checks the staged
files against `PLIST`, records input/output hashes and checks AArch64 ELF
dependencies. `CROSS_JOBS` defaults to four. Only the six canonical execution,
license and provenance files enter `stage/usr/pkg`. Models remain separate.

## Create and install the package

Transfer `stage/usr/pkg`, the recipe's `PLIST` and `DESCR`, and
`scripts/package-cross-stage.sh` to the target. Supply the actual target build
information described in the [shared instructions](README.md#target-package-and-acceptance).
Use `PKGPATH=local-ai/whisper-cpp` and
`BUILD_OPTIONS=cpu armv8-a private-static-ggml no-openmp no-gpu`.
The required base and GCC16 runtime libraries are the same as llama.cpp's.
Use the fork's actual pkg_tools and an unused package output path:

```sh
sh /tests/package-cross-stage.sh /stage/usr/pkg /recipes/whisper-cpp \
  /packages/whisper-cpp-1.9.5.tgz /recipes/whisper-build-info.txt
```

Fetch `whisper-tiny` and `jfk` with the immutable asset manifest in the
[model example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/local-inference).
Provide an actual monospace font, such as DejaVu Sans Mono, with its license.
Transfer the public `cross/run-whisper-target.sh` and `tests/whisper-runtime.sh`
while retaining their relative `ai-cpu/cross` and `ai-cpu/tests` layout.
On a disposable target with no existing Whisper package, run:

```sh
sh /tests/ai-cpu/cross/run-whisper-target.sh \
  /packages/whisper-cpp-1.9.5.tgz /models/ggml-tiny.bin \
  /fixtures/jfk.wav /fixtures/DejaVuSansMono.ttf /results/whisper
```

The check installs the package, verifies integrity and GCC16 linkage, and
transcribes the 11-second WAV with two CPU threads. It compares every word
against an independent reference. It checks malformed inputs, failed output
open/write, a missing font, successful WTS generation, batch output identity
and JSON control-character escaping. `/dev/full` is required for the write
failure case. WTS rendering and microphone capture are separate capabilities.
It removes the package, verifies removal, reinstalls it, and compares the
second transcription. It leaves the package installed.

The target shell checks text and exit statuses. Export its result directory
and complete the JSON checks on a host with Ruby:

```sh
ruby profiles/ai-cpu/tests/check-whisper-transcript.rb \
  /export/whisper/runtime/transcript /models/ggml-tiny.bin /fixtures/jfk.wav
escaped_model=$(cat /export/whisper/runtime/escaped-model-path.txt)
ruby profiles/ai-cpu/tests/check-whisper-transcript.rb \
  /export/whisper/runtime/escaped "$escaped_model" /fixtures/jfk.wav
```

The model argument is the literal guest path recorded in JSON. The WAV argument
is the exported or independently verified host fixture. The validator checks
words, model/language metadata, segment bounds against WAV duration, matching
timestamp strings, token IDs and finite probabilities. Validate `full.json`
from the failed TXT write with an explicit successful TXT reference.
Its own `full.txt` points to `/dev/full` and must not be read:

```sh
ruby profiles/ai-cpu/tests/check-whisper-transcript.rb \
  /export/whisper/runtime/full /models/ggml-tiny.bin /fixtures/jfk.wav \
  /export/whisper/runtime/transcript.txt
```

## Selected source and memory regressions

Run `test-common-utf8`, `test-whisper-buffer-loader`,
`test-whisper-zero-samples` and `test-whisper-lang-detect-abort` separately.
The last two embed the absolute build-source path ending in
`models/for-tests-ggml-tiny.bin`. Mirror that path on the guest with a symlink
to the real tiny model. The bundled header-only test fixture has no trained
weights and produces uninitialized-value diagnostics when inference runs
under Memcheck. Preserve that failed control separately; use real model
weights for the accepted inference tests.

Build the fixed-header regression against the same configured private engine:

```sh
ruby profiles/ai-cpu/tests/build-whisper-header.rb /var/tmp/whisper-cross
```

On the target, create an empty writable directory and run
`whisper-header MODEL DIRECTORY`. It checks every incomplete fixed ASR header
length, 0 through 55 bytes, through file, buffer and callback APIs, and checks
callback closure. It does not validate all variable-length model data or VAD.

Run native controls and CLI regressions under Memcheck on a supported host.
Keep their evidence distinct from target execution. The
[validation record](whisper-validation.md) records source identities,
patch contracts, analyzer limitations and the accepted VM boundary.
