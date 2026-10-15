# whisper.cpp GCC16 cross validation

Acceptance date: 2026-10-15. This record covers a Linux cross build and CPU
execution in EmberBSD AArch64 QEMU. Physical boards, microphone capture,
accelerators and transcription quality across languages remain unvalidated.

## Inputs and package

| Input | Identity |
| --- | --- |
| whisper.cpp stable release | v1.9.5, published 2026-10-06 |
| Upstream commit | `d1be6fde11ac6e0407606b4e42fe72d34add8037` |
| Source archive SHA256 | `645445da884df6dbd52b30f82d7be7c01d1767c938714e477e786b88d529e9f4` |
| EmberBSD kernel, base and sysroot | `267ee85eee1027198175809a8b7b0572df36ad1e` |
| Compiler and ABI | GCC/G++ 16.2.0, `aarch64--netbsd`, `armv8-a` |
| Source/recipe patches | `d4404390bf8a8f875bccdea277a0f1a538a28c4c` |
| Final helper guard and host validator | `7aa29e91dcc5eba7f61409ab9ec7eb586e4ccbd4` |
| Host tools | CMake 3.31.6, Ninja 1.12.1, Linux x86_64 |
| Guest | EmberBSD/NetBSD 11.0, QEMU 10.0.13 TCG, Cortex-A72, two CPUs, 2 GiB RAM |
| Package | `whisper-cpp-1.9.5.tgz`, six canonical payload files |
| Package SHA256 | `2f1cd79f6a880758ea08a0ff16f50bb3276c206365997e6f06d199a332f7be80` |
| Model | Multilingual Whisper tiny, 39M parameters, 77,691,713 bytes, MIT |
| Model repository revision | `ggerganov/whisper.cpp`, `5359861c739e955e79d9a303bcbc70fb988958b1` |
| Model SHA256 | `be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21` |
| Audio | Upstream `jfk.wav`, 11 seconds, mono 16 kHz 16-bit PCM, 352,078 bytes |
| Audio SHA256 | `59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e` |
| WTS test font | DejaVu Sans Mono, Debian fonts-dejavu-core 2.37-8, license preserved |

The compiler runtime, ELF loader, libc and pkg_tools come from the recorded
fork/toolchain. The package records actual required libraries and `/usr/pkg`
ownership. It installs three executables, source provenance and two license
files. Models and fonts are separate assets. The full public build helper
was replayed after all seven patches; checksum and existing-output rejection
also passed. No invented compiler package or package database is used.

## Installed behavior

The real package is installed alongside `llama-cpp-0.6.0nb1`. Integrity and
GCC16 linkage checks pass. Whisper tiny transcribes the JFK recording with
two threads, one processor, greedy decoding, English, no temperature fallback
and no GPU. CPU flash attention retains the upstream default. TXT and parsed
full JSON contain the independently checked reference:

> And so my fellow Americans ask not what your country can do for you,
> ask what you can do for your country.

The first invocation takes 268.48 seconds wall time and reaches 151,420 KiB
maximum resident memory. These are TCG measurements. JSON has one segment
bounded by the real 11-second audio duration and valid token probabilities.

Missing audio returns 2; invalid model magic returns 3. Undecodable audio,
failed output open/write, missing WTS font and mixed missing/valid inputs
return 11. A failed TXT write to `/dev/full` still permits valid full JSON.
Successful WTS generation uses the real font. Batch output uses the original
valid input's prefix. A model filename with newline, tab, control byte,
quote and backslash produces valid JSON preserving the literal path.

Removal deletes all three tools and the package registration. Reinstallation
passes integrity checks and reproduces the exact first transcript. The
coinstalled llama.cpp version and integrity remain valid through this cycle.

Four selected upstream tests execute on the guest: common UTF-8, buffer
loading, zero samples and language-detection abort. The model-dependent tests
use actual trained tiny weights. The fixed-header regression exercises every
incomplete length 0–55 through three real loader APIs, plus NULL-buffer and
callback-close contracts. The allocator regression checks successful lifetime
management and both injected OOM paths with `NDEBUG`.

## Patch and memory contracts

Seven AI-assisted local patches preserve upstream authorship and licenses.
No upstream acceptance is claimed:

- Two GGML metadata allocations gain unconditional `GGML_ASSERT` checks.
- CLI output failures propagate through the existing failure exit status 11.
  The shared output factory owns flush/close, including successful WTS output.
- Batch inputs retain their original output-prefix indices after missing files.
- JSON escapes all control bytes, quotes and backslashes without temporary heap ownership.
- Missing WTS fonts fail; successful script generation uses a real font.
- CSV frees each escaped segment string after writing it.
- ASR loaders reject incomplete fixed headers and preserve actual callback read counts.

Native GCC16 controls run under Valgrind Memcheck 3.24.0 on Linux x86_64.
The CSV control loses 109 bytes in two blocks before the fix. Afterward,
full JFK inference with all eight formats and failed-TXT/later-JSON output
both report zero errors and zero definitely, indirectly or possibly lost bytes.
Each retains eight reachable bytes in static GGML backend metadata.
No suppression is used. JSON parsing independently checks exact words,
metadata, timestamps and token probabilities.

The baseline fixed-header test fails on uninitialized model metadata under
Memcheck. The patched 56-prefix, three-API test frees all allocations and
reports zero errors. The allocator baseline fails its OOM contract in debug
and release. UBSan confirms null stores; optimization can change the baseline
failure from SIGSEGV to an ordinary child exit. Patched variants require the
correct assertion and SIGABRT. Their successful lifetime path has three
allocations, three frees and zero errors or leaks.

The four native upstream controls pass Memcheck with trained weights for
inference. The initial language-abort run using the bundled header-only model
reports uninitialized tensor data. That control remains failed in the evidence;
replacing its input with verified trained weights yields zero errors and
only the same eight reachable backend bytes. No test or assertion is disabled.

## Source analysis and limits

Cppcheck 2.17.1 compares the engine, CLI, GGML allocator and common-whisper
translation units before and after the patches. Each run uses its actual
GCC16 AArch64 compile context, target headers, macros and language standard.
The adapter passes the exact GCC macro dump through Cppcheck's supported
`--include` option. It removes duplicate imported `-D` arguments whose string
quotes Cppcheck otherwise loses. The seven allocator OOM warnings disappear.
No new error or OOM diagnostic appears in these four units. Inherited header
warnings and style findings remain; this is not a clean-upstream claim.

An earlier 36-unit project import failed to honor GCC-style forced includes.
It selected an incorrect miniaudio branch and misparsed version strings.
Those reports remain exploratory, not proof of effective 36-unit coverage.
Direct preprocessed-input experiments also encounter target-header parser
limitations. The corrected four-unit comparison is the accepted bounded run.

Unchanged Cppcheck findings include benchmark-only allocation paths in
`whisper_bench_memcpy_str`, and broader GGML logging, backend and quantization
allocation paths found in exploratory analysis. They remain owned by upstream
Whisper/GGML and Ports follow-up work. The WAV inference contract does not
claim these allocation-failure paths are fixed. No diagnostic category is disabled.

Clang Static Analyzer 19.1.7 uses the actual target sysroot/header context for
the engine and CLI, with recorded GCC-to-Clang argument adaptations. The CSV
leak disappears after its fix. An existing CLI warning assumes an invalid
process-entry argv; an engine token warning has inconsistent vector-capacity
conditions. Two existing dead stores remain. The new header regression has
zero Clang diagnostics and one Cppcheck const-reference style suggestion.
GCC16 `-fanalyzer` and Clang allocator controls miss the demonstrated baseline
OOM defects; the red/green execution tests provide the decisive evidence.

The bounded header fix does not validate arbitrary variable-length filters,
vocabulary, tensor payloads or VAD models. Existing invalid CLI-option status
behavior and general model-format hardening remain outside these patches.
WTS script generation does not establish FFmpeg rendering. Native Memcheck
controls do not instrument AArch64 guest binaries. TCG timings do not estimate
physical-board performance or establish continuous-service reliability.

## Reproduce

Use the [Whisper cross instructions](whisper.md). Retain the immutable source
archive, recipe patches, toolchain/sysroot identity, compiler commands,
build logs, ELF and file manifests, native red/green reports, target console,
package metadata, transcripts, parsed JSON, error statuses and archive hashes.
The accepted guest boots the recorded kernel and a standalone FFS image.
Its test transport is isolated from external networks; inference reads local files.

The initial cloud root completed every application/package contract, then
failed to archive its logs: `/usr/bin/tar` pointed to absent `/bin/tar`.
The completed receipts were exported individually over the isolated transport;
the failed guest archive step remains recorded. Adding the fork's actual
`/bin/tar` completed the replay root. A separate AArch64 guest verified native
gzip-tar creation/extraction, byte comparisons, control filenames, an empty
file, a symlink and clean shutdown. The full model cycle precedes that
filesystem-only export correction; it was not repeated afterward.
