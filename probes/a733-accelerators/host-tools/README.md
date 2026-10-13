# Native PowerVR compiler tools

This probe builds genuine Mesa compiler tools on macOS ARM64. It prepares
USC programs for a later A733 compute test. It does not execute GPU code.
It does not enable the PowerVR Vulkan driver in the common Mesa recipe.

The exact A733 BVNC is `36.56.104.183`. Mesa also has a different BVNC with
the public name `BXM-4-64`. That name selects `36.52.104.182` first. Use the
explicit BVNC argument for the A733 profile. This profile remains experimental.
No feature assertions or IR validation checks are disabled.

## Inputs

Use a separate source copy and build directory. Keep the shared LLVM SDK and
target Mesa sources unchanged. Use the current common host tools from
[common-build-tools](../../../profiles/common-build-tools/README.md).

| Input | Pin |
| --- | --- |
| Mesa archive | 26.2.4, SHA256 `bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9` |
| Native LLVM SDK | 23.1.3, archive SHA256 `3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1` |
| SPIRV-LLVM-Translator | [v23.1.2](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/tree/e65dde28ce8f12ef7245914fa2850260328669e4), commit `e65dde28ce8f12ef7245914fa2850260328669e4` |
| SPIRV-Tools | [v2026.4](https://github.com/KhronosGroup/SPIRV-Tools/tree/ef96ed763b43b59b33b31b362f09a02b729fa1c9), commit `ef96ed763b43b59b33b31b362f09a02b729fa1c9` |
| SPIRV-Headers | Tools v2026.4 DEPS pin [`496543121ce6419f23d6fa5d7194ba66c36212d2`](https://github.com/KhronosGroup/SPIRV-Headers/tree/496543121ce6419f23d6fa5d7194ba66c36212d2) |

Translator 23 matches LLVM 23. The translator main branch targets LLVM 24.
Use the same Headers checkout for Tools and Translator. Build their static
libraries and command-line tools into one isolated dependency prefix.
Keep Translator assertions and SPIRV-Tools warnings enabled.

Mesa uses upstream Python generators. The checked host uses Python 3.14.8,
Meson 1.12.1, Ninja 1.13.2, CMake 4.4.4, lxml 6.1.3, and rnc2rng 2.7.0.
Install missing generator modules in a local virtual environment. Do not omit
XML schema validation. These helpers add no new Python implementation.

The native SDK contains LLVM bitcode archives. Linking them performs LTO.
The wrapper uses LLVM LLD with optimization level 1. Assertions remain on.
It explicitly selects the current macOS C++ runtime. An `-L` path from
`llvm-config` must not silently select the SDK's separate C++ runtime.
This is a host tool choice. It does not change the target runtime policy.

## Build and generate

Apply [mesa-26.2.4-pco-bvnc.patch](mesa-26.2.4-pco-bvnc.patch) to the isolated
Mesa source. Apply the [IDFWDF layout patch](../idfwdf/mesa-26.2.4-idfwdf-layout.patch)
before generating common shaders. The shader and host IDFWDF layout must both
use ten dwords. Old generated IDFWDF programs are not valid with that layout.

`configure-host.sh WORK MESA_SOURCE LLVM_SDK HOST_PREFIX DEP_PREFIX` configures
and builds the native tools. Use absolute paths without whitespace or quotes.
The local virtual environment, if needed, belongs at `WORK/venv`.
`JOBS` controls build concurrency and defaults to four.

The build contains `src/compiler/clc/mesa_clc` and
`src/imagination/pco/uscgen/pco_clc`. The common SPIR-V input is
`src/imagination/pco/usclib/pco_usclib.spv`. The generated common source is
`src/imagination/pco/uscgen/pco_uscgen_programs.c`.

Use the real CLI contract:

```sh
ruby check-bvnc.rb "$MESA_SOURCE" "$MESA_BUILD" "$PCO_CLC" \
    "$COMMON_SPV" "$TEST_OUTPUT"
```

The contract compiles the actual parser and device table with ASan/UBSan.
It checks actual positive and negative CLI calls. Rejected arguments must
preserve existing outputs and must not create new output files.

Use the compiler input fixtures:

```sh
sh generate-probe.sh "$MESA_SOURCE" "$MESA_BUILD" "$MESA_CLC" \
    "$PCO_CLC" "$SPIRV_VAL" "$PROGRAM_OUTPUT"
```

`cs-probe-store.cl` writes `0x13579bdf` to GPU VA `0x8000000000`.
The future native GPU context must map that VA before execution.
It is not a device physical address. The input has no kernel arguments.
`cs-probe-nop.cl` provides a separate compiler baseline.

The script records NIR, PCO, and binary dumps. `KERNEL(1)` alone does not prove
that a padded hardware dispatch executes one lane. The precompiled shader
path marks shaders internal. The automatic compute instance check skips
internal shaders. A later packet producer must resolve this execution
condition before the store program can run on hardware.

## Verification boundary

Source review and host code generation do not prove GPU execution. Keep
compiler commands, source pins, patch hashes, program hashes, and actual
metadata with each generated artifact. Do not write generated GPU binaries
into Git. Decode the eight-byte prefix with Mesa's actual `pco_precomp_data`
definition. Do not guess its packed bitfields.

The parser has a source-derived ASan/UBSan contract. The two changed translation
units are checked with Clang Static Analyzer using their actual native compile
commands. GCC 16 path analysis covers the extracted parser and original BVNC
pack macros. Cppcheck 2.22 has macOS 27 header and Clang AST import limitations;
record those separately from parser findings. macOS ARM64 has no supported
Valgrind Memcheck run here. ASan/UBSan is a separate check.

The patches are AI-assisted downstream changes. They have not been submitted
to or accepted by Mesa upstream. Original Imagination and other attribution
remains in the source.
