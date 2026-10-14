# llama.cpp GCC16 cross validation

Validated on 2026-10-14. The host cross-builds the application. The EmberBSD
guest creates and installs a real pkg_tools archive, then executes the model.
This establishes CPU inference in this VM. It does not establish physical
board performance, GPU/NPU support or long-duration service reliability.

## Provenance

| Input | Identity |
| --- | --- |
| llama.cpp | 0.6.0, `8345f333951c661d166b00e6f9362e553768f292` |
| Source archive SHA256 | `84050e783dbd0c4a4678f90f253b0881df04e90a98c20f73ae3709751c4a4850` |
| EmberBSD kernel and sysroot source | `267ee85eee1027198175809a8b7b0572df36ad1e` |
| Ports pkgsrc pin | `fff4deb639a1a640476203c80f752fb77b6cb14b` |
| Compiler | GCC/G++ 16.2.0, `aarch64--netbsd` |
| Build tools | CMake 3.31.6, Ninja 1.12.1, Linux x86_64 container |
| Guest | EmberBSD/NetBSD 11.0, AArch64, QEMU 10.0.13 TCG, Cortex-A72, two CPUs, 2 GiB RAM |
| Model | SmolLM2-135M-Instruct Q4_K_M, 105,454,432 bytes, Apache-2.0 |
| Model revision | bartowski/SmolLM2-135M-Instruct-GGUF, `09816acd5d99df7be770d85ea30822623dab342c` |
| Model SHA256 | `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d` |

The kernel, libc, headers and additional pkgtools libraries come from that
fork revision. Base pkgtools version is 20260227. OpenSSL is the fork's 3.5.7
implementation. No original NetBSD binary sets replace fork components.
The application uses private static engine/GGML archives and the target's
`libstdc++.so.7`, `libgcc_s.so.1`, libc, libm and libpthread. ELF checks reject
host RPATHs. CPU features match the native package policy.

## Installed behavior

The target package contains the nine canonical `PLIST` files. `pkg_create`
records root/wheel ownership and `/usr/pkg` as its installation prefix.
`pkg_add` checks the real required libraries. No fake compiler package is
registered. `pkg_admin check` verifies all nine files before and after
removal/reinstallation. The five selected programs are AArch64 ELF files.

SmolLM2 uses two threads, a 512-token context, seed 1 and temperature 0.
For the prompt `The capital of France is`, 24 generated tokens include:

> Paris. Paris is a city known for its historical landmarks, art museums,
> fashion, gastronomy, and culture. It is

The loopback HTTP completion returns 16 tokens and the expected unique model
alias. The check follows its own server PID and requires successful shutdown.
An occupied port is rejected before package installation. A malformed GGUF
must return failure. The model remains a separate asset outside the package.

Five selected upstream groups pass on the target: sampling, grammar parser,
grammar integration, JSON-schema-to-grammar and GGUF. The allocator regression
also passes on the target with `NDEBUG`, including both injected OOM paths.
These checks are a selected suite, not all upstream tests.

## Memory and source checks

Cppcheck 2.17.1 initially analyzed eight translation units from the actual
target compilation database. It found two confirmed unchecked GGML metadata
allocations. The package patch adds unconditional `GGML_ASSERT` checks after
`calloc` in `new_chunk` and `malloc` in `dyn_tallocr_new`. It preserves the
existing fatal allocation contract and ABI. It is an AI-assisted local patch;
upstream acceptance is not claimed.

The regression compiles the real upstream allocator and abort handler.
Both unpatched debug and release variants crash with SIGSEGV and no assertion
diagnostic. Both patched variants emit the correct diagnostic and SIGABRT.
The successful allocation/reset/free path passes Valgrind with three
allocations, three frees, no remaining allocations and zero errors.

Target allocator Cppcheck comparison uses the same compile arguments and the
[abort model](../tests/ggml-abort.cfg), which describes the actual nonreturning
variadic function. The seven related null-allocation reports become zero
after the patch. Existing header conversion, index and style findings remain
in the evidence. No diagnostic category is disabled. This is targeted
analysis; it is not a claim that all upstream sources are free of defects.

GCC16 `-fanalyzer` reports no allocator findings at either optimization level
on either variant. It misses the demonstrated baseline defects. The regression
provides the decisive evidence. GCC16 path analysis and Clang Static Analyzer
19.1.7 report no findings in the regression fixture. Its Cppcheck findings
come from inherited upstream headers, not the fixture's control flow.

Native x86_64 GCC16 upstream control tests run under Valgrind Memcheck 3.24.0:
sampling, grammar parser, grammar integration, GGUF and quantization functions.
All five report zero errors and zero definitely, indirectly or possibly lost
bytes. Quantization retains 5,975,038 bytes in 18 reachable global lookup-table
allocations. The other four free all allocations. The patched allocator has
the separate successful-path Memcheck test above. Native controls complement
the actual AArch64 tests; they do not instrument the target ELF files.

The build retains upstream `std::filesystem::u8path` deprecation and enum
conversion warnings.
No warning suppression, analyzer-wide suppression or test disablement was
added for this port. Existing optional GPU/UI/OpenMP features remain outside
this CPU profile.

## Reproduction and evidence

Use the [cross instructions](README.md) with the recorded inputs. Preserve
the host configure/build logs, ELF report and compilation database. Preserve
target serial output, package creation and integrity logs, generated text,
HTTP response, test logs and package SHA256. Compare unpatched and patched
allocator XML reports with identical compiler arguments. The regression
script records its compiler, source hashes and both debug/release outcomes.

The accepted VM uses direct kernel boot and a standalone FFS root image.
Its export transport is isolated from external networks. The inference
server binds to guest loopback. Inference reads a local GGUF file.
