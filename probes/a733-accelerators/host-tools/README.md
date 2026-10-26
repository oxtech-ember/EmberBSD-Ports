# Native PowerVR compiler tools

This probe builds genuine Mesa compiler tools on macOS ARM64. It prepares
USC programs for a later A733 compute test. It does not execute GPU code.
It does not enable the PowerVR Vulkan driver in the common Mesa recipe.

The exact A733 BVNC is `36.56.104.183`. Mesa also has a different BVNC with
the public name `BXM-4-64`. That name selects `36.52.104.182` first. Use the
explicit BVNC argument for the A733 profile. This profile remains experimental.
No feature assertions or IR validation checks are disabled.

## Inputs and build

Use the [shared Mesa generator producer](../../../profiles/common-graphics/cross/mesa-generators.md).
It uses host GCC16 and the common native LLVM/Clang CLC and SPIR-V packages.
Their shared Ports recipes own all dependency versions and portability patches.
The old private dependency builder and compiler wrapper have been removed.

Select `--profile powervr` or `--profile all` for the PowerVR compiler.
Use a fresh work directory. The producer keeps assertions and upstream tests enabled.
It applies the exact BVNC patch without changing the shared target Mesa sources.
The shader check also uses the canonical IDFWDF header layout.
Old programs for a different IDFWDF layout cannot be reused.

The shared SPIRV-Tools recipe owns the
[function-order fix](../../../pkgsrc/parallel/spirv-tools/patches/patch-source_link_linker.cpp).
The [real-tool regression](check-spirv-link-order.py) covers both module orders,
import-only modules, resolved imports and definitions without imports.
Run it against the installed common tools:

```sh
python3.15 check-spirv-link-order.py --sdk-source "$SDK_SOURCE" "$TOOLS_BIN" "$NEW_TEST_OUTPUT"
```

Every input and linked result passes `spirv-val`.
The checks preserve function order and imported call targets.
Use `--expect-invalid` only to reproduce the pinned unpatched failure.
Rebuild dependent tools after replacing incompatible libraries.

## Generate PowerVR programs

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
