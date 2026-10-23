# Native shader generators for Iris and PowerVR

Mesa 26.2.5 uses CLC for Iris shaders even when Rusticl is disabled.
The default `mesa-clc=auto` selects the target CLC dependency closure.
It conflicts with the common recipe's disabled target SPIRV-Tools option.
Iris therefore uses `mesa-clc=system` and `precomp-compiler=system`.
Mesa runs native `mesa_clc` and `vtn_bindgen2` through its native file.
The target compiler remains on the development host.

The [PowerVR workflow](powervr.md#native-build-tools) already prepares these
two generic tools. `pco_clc` is specific to PowerVR and is optional for an
Intel-only seal. The target package still builds the complete Iris shaders.
No shader path or driver feature is disabled to avoid the host dependency.

## Prepare the native tools

Use the original [Mesa host-tool inputs](../../../probes/a733-accelerators/host-tools/README.md#inputs):

- Mesa 26.2.5, SHA256 `794b3d1729075dae7ebd47c7283b7ca0cdb5dec668f7f11cc0a5d82f6138a0a5`.
- Full LLVM 23.1.3 macOS ARM64 SDK, SHA256 `3dcfd88aec10be204a24037bcb0dc0ad777882e9dbe8ac60e2639060d8a794b1`.
- SPIRV-LLVM-Translator 23.1.2, commit `e65dde28ce8f12ef7245914fa2850260328669e4`.
- SPIRV-Tools 2026.4, commit `ef96ed763b43b59b33b31b362f09a02b729fa1c9`.
- SPIRV-Headers, commit `496543121ce6419f23d6fa5d7194ba66c36212d2`.

Use the existing `build-deps.py` and its SPIRV-Tools function-order fix.
Keep the same Headers source for Translator and Tools. Build static libraries
and retain the actual `spirv-val` executable and its source receipt.
The LLVM SDK must supply Clang CLC libraries and headers, static LLVM support,
`llvm-config`, `llvm-ar`, Clang and LLD. Preserve the native macOS C++ runtime
selection and assertions from the existing host-tool configuration.
A separate target LLVM metadata helper cannot replace this native SDK.

Build tools include Meson 1.12.1, Ninja 1.13.2, CMake 4.4.4, pkg-config,
the macOS SDK and `otool`. Use the shared native Python 3.15 with
Mako, packaging, PyYAML, lxml and rnc2rng from their normal pkgsrc packages.
The rnc2rng package uses the shared rply and appdirs dependencies.
They are native build dependencies. They are not installed in the target VM.

Use a fresh source copy and the existing `configure-host.sh` configuration.
Its complete build also prepares PowerVR's compiler. The Intel seal does
not require that compiler executable. It does require the genuine upstream
common-shader command in `build.ninja`, generated Clang OpenCL header arrays,
and the real compile/link metadata. Do not fabricate these files.
The native source must match the original archive. The existing optional
exact-BVNC patch is the only accepted native source delta.

## Scripted build

The Python standard-library orchestrator uses SDK host API1:

~~~sh
"$HOST_PREFIX/bin/python3.15" -B scripts/build-mesa-generators.py \
    --sdk-source "$SDK_SOURCE" --host-prefix "$HOST_PREFIX" \
    --profile intel --jobs 10 /absolute/new-work /absolute/distdir
~~~

The work directory must be absent. A failed build retains its partial work.
Use a new directory for a new attempt. The command checks the pinned archives,
Khronos revisions, native package predicates and Python module origins.
It does not create a virtual environment or install Python modules.
Install missing dependencies through their normal pkgsrc recipes.

The selected native LLVM/Clang SDK builds host-only compiler tools.
The target Mesa objects still use the common GCC16 cross toolchain.
The command calls the existing native configuration and real shader checks.
The sealed result is in WORK/sealed.

## Seal and select capabilities

```sh
python3.15 seal-mesa-generators.py --sdk-source "$SDK_SOURCE" --profile intel \
    /absolute/mesa-26.2.5.tar.xz /absolute/native-mesa-source \
    /absolute/native-mesa-build /absolute/spirv-val /absolute/new-intel-tools
```

`--profile powervr` remains the default and retains the original three tools.
`--profile all` seals both capabilities for an Iris plus PowerVR selection.
Each seal binds `PROFILES` through `installed.sha256`. An older seal without
that file is accepted only for the existing PowerVR path.
The recipe rejects missing capabilities before running a generator.

The Intel seal copies only `mesa_clc` and `vtn_bindgen2`. It retains the real
common OpenCL to SPIR-V, validator and NIR smoke steps. It omits PCO execution.
It binds the target NIR interfaces and the eight upstream Intel shader inputs.
The receipt distinguishes this generic compiler check from full Intel shader
generation. The latter is checked by the subsequent target Mesa build.
This workflow does not qualify Iris rendering, KMS, input or a Plasma session.

Set `EMBERBSD_MESA_GENERATORS=/absolute/new-intel-tools` in the private
cross MAKECONF. The x86_64 Mesa recipe selects Iris and both system generators.
Its native Meson file contains no `pco_clc` entry unless PowerVR is also selected.
Target SPIRV-Tools, Translator and Clang CLC libraries are not required by
this path. Keep the selected target LLVM runtime for llvmpipe and ORC.

## Host regressions

```sh
BMAKE=/absolute/native/bmake ruby ../tests/mesa-generator-profiles.rb
BMAKE=/absolute/native/bmake ruby ../tests/amd64-targets.rb
ruby ../tests/iris-clc-configure.rb /absolute/native/python3.15 \
    /absolute/meson-1.12.1/meson.py /absolute/mesa-26.2.5
```

The profile fixture runs the production shell verifier and native-file target.
Its marker tools are never executed. It checks capability binding, changed
bytes, missing tools, legacy behavior and an Intel-only native file.
The Meson fixture extracts the actual upstream CLC selection and SPIRV-Tools
feature checks. Real Meson must reject the old auto/disabled combination
and configure successfully with the native generator selection.
It creates no Mesa compiler objects and runs no target code.

The implementation changes Ruby, shell and make orchestration only.
It changes no upstream C/C++ translation unit. Full native tool rebuild,
sealing and target Mesa package checks remain separate acceptance steps.
