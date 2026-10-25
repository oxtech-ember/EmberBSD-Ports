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
| Mesa archive | 26.2.5, SHA256 `794b3d1729075dae7ebd47c7283b7ca0cdb5dec668f7f11cc0a5d82f6138a0a5` |
| Native LLVM SDK | 23.1.3, archive SHA256 `3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1` |
| SPIRV-LLVM-Translator | [v23.1.2](https://github.com/KhronosGroup/SPIRV-LLVM-Translator/tree/e65dde28ce8f12ef7245914fa2850260328669e4), commit `e65dde28ce8f12ef7245914fa2850260328669e4` |
| SPIRV-Tools | [v2026.4](https://github.com/KhronosGroup/SPIRV-Tools/tree/ef96ed763b43b59b33b31b362f09a02b729fa1c9), commit `ef96ed763b43b59b33b31b362f09a02b729fa1c9` |
| SPIRV-Headers | [vulkan-sdk-1.4.363.0](https://github.com/KhronosGroup/SPIRV-Headers/tree/496543121ce6419f23d6fa5d7194ba66c36212d2), Tools v2026.4 DEPS pin `496543121ce6419f23d6fa5d7194ba66c36212d2` |

Translator 23 matches LLVM 23. The translator main branch targets LLVM 24.
Use the same Headers checkout for Tools and Translator. Build their static
libraries and command-line tools into one isolated dependency prefix.
Keep Translator assertions and SPIRV-Tools warnings enabled.

The dependency builder applies the shared recipe's
[linker fix](../../../pkgsrc/parallel/spirv-tools/patches/patch-source_link_linker.cpp)
to this exact SPIRV-Tools revision. It verifies the source hash and rejects
unrelated source changes. The original linker puts declarations from later
modules after earlier definitions. Such partial libraries fail `spirv-val`.
The fix preserves declaration and definition order within their groups.
It does not change function names, call targets, or linkage resolution.
This AI-assisted downstream patch retains the upstream Apache-2.0 license.
It has not been submitted to or accepted by SPIRV-Tools upstream.
The recipe owns the patch. The host helper consumes both canonical source
patches with `git apply -p0`; it does not maintain another implementation.
The installed GoogleTest and Effcee options stay OFF in this existing host
workflow. The shared native recipe enables both options and uses the common
GoogleTest, Effcee and RE2 providers for its full unit suite.
The helper verifies all expected patched files and the exact Git status.
It can resume a known subset after interruption and rejects other edits.
Recipe integration is checked at the source level. New native package builds
and their consumer checks remain separate acceptance steps.

The builder runs the [real-tool regression](check-spirv-link-order.py) before
installing SPIRV-Tools. Run it separately with:

```sh
python3.15 check-spirv-link-order.py --sdk-source "$SDK_SOURCE" "$TOOLS_BIN" "$NEW_TEST_OUTPUT"
```

The five cases cover both module orders, an import-only module, resolved
imports, and definitions without imports. Every input and linked result
passes `spirv-val`. The checks preserve function order and imported call
targets. Use `--expect-invalid` only with the pinned unpatched tools to
record the three causal validator failures. Rebuild Mesa's `mesa_clc`
after replacing its static SPIRV-Tools libraries. Previously generated
SPIR-V and compiler binaries do not acquire this fix automatically.

Mesa uses upstream Python generators with the shared native Python 3.15.
Use Meson, Ninja, CMake, Mako, packaging, PyYAML, lxml and rnc2rng from
normal pkgsrc packages. The rnc2rng recipe supplies its shared rply dependency.
Do not omit XML schema validation. No pip or virtual environment is required.
The dependency builder accepts HOST_PYTHON and an explicit
EMBERBSD_SDK_SOURCE. The top-level Python builder checks package predicates,
module origins and the libyaml extension before it starts a build.

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
Use HOST_PREFIX/bin/python3.15 and its installed generator modules.
`JOBS` controls build concurrency and defaults to four.

The build contains `src/compiler/clc/mesa_clc` and
`src/imagination/pco/uscgen/pco_clc`.
Generate the acceptance shaders through the checked compiler closure:

```sh
ruby generate-usclib.rb "$MESA_SOURCE" "$MESA_BUILD" \
    "$SPIRV_DIS" "$SPIRV_VAL" "$NEW_PROGRAM_OUTPUT"
```

The command copies the pinned shared header into an isolated include overlay.
It applies the same IDFWDF change as the CPU image generator.
It does not modify the Mesa source or its generated cache.
It uses the real build's compiler arguments and records every executed command.
SPIR-V validation remains enabled.
The PCO step uses `PCO_DEBUG=no_pred_cf`, as specified by upstream
`src/imagination/pco/uscgen/meson.build` for its common shader table.
This disables predicated control flow; it does not set `val_skip`.
The receipt records this environment and the source of that build option.
The PCO step also records NIR and binary diagnostic output.
The checked IDFWDF input reads descriptor slots 0 and 4, then address slots 8 and 9.
The receipt binds the header, compiler tools, shader input, and generated table by SHA256.
A matching host header is required when the image generator consumes these shaders.
An old generated table cannot prove its ABI with a manually assigned dword count.

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

The script records NIR, PCO, and binary dumps.
`KERNEL(1)` does not restrict a padded hardware dispatch by itself.
The store source explicitly returns when `nir_load_instance_num_pco()` is nonzero.
It uses the upstream internal `nir_dma_st_pco` intrinsic with two address dwords.
PCO does not yet lower a generic OpenCL store through a 64-bit constant pointer.
The proof rejects generic writes, unknown calls, store loops, and nonconstant DMA arguments.
The checked common compiler closure verifies that branch in the actual SPIR-V.
Only the zero-instance path can reach one 32-bit store of `0x13579bdf` to `0x8000000000`.
Unknown compiler control-flow shapes fail the check.
This compiler check does not prove GPU execution or cache visibility.

## Shader ABI regression

Run the regression with a saved disassembly of the original common SPIR-V:

```sh
ruby ../idfwdf/check-usclib.rb "$MESA_SOURCE" "$OLD_SPIRV_TEXT" "$NEW_TEST_OUTPUT"
```

The contract rejects the original 5/6 address slots and an unsubstantiated layout flag.
It also rejects stale hashes, a wrong store address or width, missing guards, and extra stores.
Compiler execution and physical acceptance are separate from these parser contracts.

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
