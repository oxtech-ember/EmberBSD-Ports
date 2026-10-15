# ONNX Runtime validation

The selected provider is ONNX Runtime 1.31.0, GCC 16.2.0, C++20, a shared
CPU execution library and common Eigen 5.0.1. The build retains standard
ONNX operators. The source, patches, dependency pins and feature boundaries
are described in [PROVENANCE.md](PROVENANCE.md) and [README.md](README.md).

## Cross build and installed SDK

The actual GCC 16.2.0 AArch64 build completed with nine runtime patches and
one MLAS test-harness patch. All ten apply without fuzz.
Warnings remain errors. The final link retains the upstream strict unresolved
symbol check. Both `onnxruntime` and `onnxruntime_providers_shared` are explicit
build targets; the upstream install rules require the second library too.

The exact staged package contains **49 paths**: nineteen public headers,
four CMake files, one pkg-config file, two shared libraries with two runtime
symlinks, and twenty-one source/license notices. The package PLIST matches
that file list. It does not publish private dependency development packages.

Both shared objects are AArch64 ELF files. Their runtime dependencies use
the coherent base libraries and GCC16 `libstdc++.so.7`/`libgcc_s.so.1`.
The main runtime SONAME is `libonnxruntime.so.1`. Runtime search paths contain
target package locations and no build-host directories.

The CMake exports compute their installed prefix relative to their files.
A byte-verified copy of the complete SDK configured and built the installed
Add/Relu, affinity and Silero C++ consumers in a separate directory.
The complete C example also compiled with the actual `libonnxruntime.pc`
flags and `PKG_CONFIG_SYSROOT_DIR`. These metadata checks are separate from
the target inference execution below.

## Constructor regression

The reusable [full-source control](check-selector-registry.rb) passed with
the actual AArch64 compilation database. GCC16 reports the original
construction-phase `maybe-uninitialized` diagnostic. The canonical free
factory compiles with the same `-O2 -Werror` flags. The class declaration
remains byte-identical. No reduced implementation or substitute API is used.

## Native installed controls

The Linux x86-64 host control uses GCC 16.2.0 and the same nine runtime
adaptations and CPU feature profile. Its independent installed consumers pass
**2/2 CTests**. The provider registry contains only `CPUExecutionProvider`.

- Add/Relu: exact expected values over 100 runs; malformed model, wrong
  input shape and unknown input-name rejection.
- Existing Silero 6.2.3: 1,008,000 samples, 1,969 frames and 1,450 speech
  frames. Whole-buffer and arbitrary-chunk inference agree. State continuity,
  padding, silence boundaries and invalid PCM/sample-rate rejection pass.
  The fixed 0.5 threshold gives first/last boundaries of 1.024/61.024 seconds.
  These are compatibility outputs, not speech accuracy measurements.

Valgrind **3.24.0** Memcheck passes four independent processes: Add/Relu,
valid Silero inference, malformed Silero model and malformed WAV. Expected
application statuses are respectively 0, 0, 1 and 1. Every process has zero
memory errors, zero suppressions and no heap blocks remaining at exit.
The checks enable origin tracking and full leak detection; definite,
indirect and possible leaks cause failure. `LD_LIBRARY_PATH` is unset.
Loaded runtime and GCC16 libraries resolve from the selected installation.
The final rebuild's shared libraries and rebuilt consumers match the
Memcheck-tested binaries byte for byte.

The complete C example compiles with the actual native pkg-config metadata.
The runtime reports an unknown CPU vendor with cpuinfo disabled; these
checks do not establish vendor-specific tuning or multi-core throughput.

## EmberBSD installed-package acceptance

The complete acceptance passed in AArch64 EmberBSD under QEMU TCG, with two
Cortex-A72 CPUs and 2 GiB RAM. The kernel, base libraries and sysroot come
from fork revision `267ee85eee1027198175809a8b7b0572df36ad1e`.
The compiler is GCC 16.2.0; the target C++ runtime is `libstdc++.so.7`.
No upstream NetBSD release sets replace the fork's components.

The guest creates a real `onnxruntime-1.31.0` package from the final cross
stage. It installs it with pkgtools, checks all 49 files, executes the tests,
removes it, verifies header/library removal, reinstalls it and repeats the
installed consumers. Every packaged byte, mode and symlink matches the
cross stage. The GCC16 runtime is already present in this acceptance image.
This is cross-package acceptance, not a full native pkgsrc bootstrap test.

- Both installed APIs execute the 421-byte `Gemm -> Relu -> Gemm` model.
  Batches 1, 3 and 32 use respectively 1, 100 and 4 repeated runs.
  Each API produces 429 rows per installation. A separate scalar checker
  validates every input, output, row order and row count at tolerance `1e-5`.
  It does not link ONNX Runtime or share model/application code.
- A third complete C consumer is built with the installed
  `libonnxruntime.pc`. Its results match the CMake C consumer byte for byte.
  C and C++ results also match after package reinstallation.
- Wrong shapes and input/output names return `ORT_INVALID_ARGUMENT`.
  Malformed and missing model files return `ORT_INVALID_PROTOBUF` and
  `ORT_NO_SUCHFILE`. Both APIs preserve an existing output file on all ten
  model/inference error cases.
- The existing Add/Relu contract passes 100 repeated runs per installation.
  Eight sessions create and destroy real default workers: two intra-op
  threads mean the caller plus one worker. Their 64 dynamic-batch runs
  independently check 832 samples per installation.
- Real worker affinity and current-CPU checks pass on both guest CPUs.
  Source-level POSIX controls expose five original cleanup/error failures
  and pass all five patched cases, including an explicit stack size.
  This source control does not invent a public ORT worker-stack option.
- The pristine BFloat16 header passes the GCC16 target numerical control.
  Strict C17 and C++20 controls verify the fixed C header's signed enum
  value, size, alignment, containing layout and `0x80000000` reason mask.
  The pristine and patched C++ ABI outputs match.
- Silero repeats the native compatibility outputs stated above. Whole and
  arbitrary-chunk streams agree, malformed models/WAVs are rejected, and
  results match after reinstallation.

The first full accepted run took about two minutes under TCG. This is not
a throughput measurement. `run-target.sh` retains the real loader paths,
package checks, CSVs, errors and upstream XML. The host checks the exported
CSVs independently after the guest run.

## Selected upstream tests and guarded memory

All **76 tests in 13 suites** pass in the target, with zero failures,
disabled cases or skips. They cover narrowing, checked arithmetic, strings,
UTF8, six convolution-buffer overflow cases and eight transpose cases.
Transpose checks every dimension from 1 through 32 against a reference;
threaded cases use real production thread support and archives.

The seven test translation units remain unchanged. Their shared MLAS test
header has the canonical portability patch. The original header aborts
before its first transpose under PaX: `mmap(PROT_NONE)` succeeds, then the
undeclared RW upgrade fails with `EACCES`. The fixed NetBSD mapping declares
future RW permissions with `PROT_MPROTECT` and keeps the upper guard
inaccessible. A child that reads past the data bound still receives SIGSEGV.
Another actual-header control injects `MAP_FAILED`; the original proceeds
to `mprotect`, whereas the fixed code stops at the allocation failure.
Neither the guard nor kernel protection is disabled.

Native selected tests pass again under strict Memcheck after this harness
change. Header ABI controls pass 2/2 CTests; guarded-buffer controls pass
4/4 CTests. Patched mapping and allocation-failure processes also pass strict
Memcheck. The intentional guard-child fault is a separate ordinary negative
control, not a clean Memcheck result.

The standalone example additionally passes 2/2 native CTests and **58 strict
Memcheck processes**. Every process has zero memory errors, lost or reachable
bytes, and suppressions. Final rebuilt native applications and runtime
match those tested files byte for byte.

## Source analysis and limits

Cppcheck 2.17.1 and Clang Static Analyzer 19.1.7 use actual AArch64 compiler
commands, target headers, measured sizes and recorded macro/header hashes.
Six runtime units pass Clang in the eight-patch source profile. Cppcheck has recorded
Eigen/SAL parser gaps and 120-second limits in large fused/registry units;
these are incomplete checks. Historical eight-patch contexts are preserved
separately from the later public-header and allocator controls.

The C header's signed-shift defect has a complete actual-preprocessed C
Cppcheck red/green control. The fixed C example's compilation-database check
passes. All four example translation units pass target Clang analysis.
Cppcheck cannot parse selected GCC16 C++ `<array>` attributes; its experimental
Clang backend also failed to preserve target selection. GCC `-fanalyzer`
reaches a recorded complexity limit in the full C application's cleanup
paths. Those runs do not establish complete source coverage.
The focused header C control passes GCC path analysis. Focused POSIX and
allocator controls retain their exact baseline/final diagnostics. No broad
diagnostic category is disabled to claim success.

CPU inference, selected tests and native memory checks do not validate every
operator, model accuracy, microphone capture, real-time performance, physical
boards, training, or GPU/NPU execution. Existing ncnn and RNNoise measurements
remain separate historical source-probe evidence.
