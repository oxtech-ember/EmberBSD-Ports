# Native shader generators for Iris and PowerVR

Mesa 26.2.5 uses CLC for Iris shaders even when Rusticl is disabled.
The default `mesa-clc=auto` selects the target CLC dependency closure.
Cross builds instead use `mesa-clc=system` and `precomp-compiler=system`.
Mesa runs native `mesa_clc` and `vtn_bindgen2` through its native file.
The target compiler remains on the development host.

Native NetBSD builds use Mesa's in-tree generators and build-only CLC library
dependencies. They do not need a sealed cross-host generator directory. See the
[recipe selection and metadata check](../../../pkgsrc/graphics/MesaLib/tests/README.md#native-and-cross-shader-generators).

The [PowerVR workflow](powervr.md#native-build-tools) already prepares these
two generic tools. `pco_clc` is specific to PowerVR and is optional for an
Intel-only seal. The target package still builds the complete Iris shaders.
No shader path or driver feature is disabled to avoid the host dependency.

## Prepare the native tools

Sealed generators support Darwin arm64 with Clang or GCC and Linux x86_64 with
Clang. The host record binds each seal to its OS, CPU and compiler family.
Format 2 seals carry this record, and the verifier rejects a different host ABI.
Format 1 keeps its existing verifier contract and interface checks.

Use one native Ports prefix with Clang/LLVM by default. The shared recipes own
LLVM, Clang CLC libraries, SPIRV-Headers, SPIRV-Tools and SPIRV-LLVM-Translator.
Do not download a binary compiler or build a private dependency stack.
The native LLVM and Clang libraries and the generators need a compatible host
C++ runtime. GCC16 remains an explicit host compiler alternative.

The current inputs are Mesa 26.2.5, LLVM/Clang 23.1.4, Translator 23.1.2,
SPIRV-Tools 2026.4, SPIRV-Headers 1.4.363.0 and GoogleTest 1.18.0.
Use the common Ports patches and the external GoogleTest provider for tests.
The producer checks package predicates, Python module origins and the libyaml extension.
Build missing dependencies through their normal pkgsrc recipes before starting this producer.

SDK `load_host_prefix` selects tools, checks their native CPU and resolves their paths.
It also checks the selected compiler components and script interpreters.
No separate toolchain qualification or acceptance receipt is required.
The build uses a prefix-only PATH and an explicit Meson native file.
Host ABI headers and libraries remain inputs from the selected host OS.
Target include, library and pkg-config paths do not enter this native build.
Linux sealing validates ELF64 x86_64 binaries and their loader closure with the
selected prefix's `llvm-readelf` and the system `/usr/bin/ldd`.

The full native build prepares the generic CLC tools and PowerVR's compiler.
An Intel seal does not copy or execute the PowerVR compiler.
It still checks the genuine upstream common shader command and compile/link metadata.
Assertions, SPIR-V validation and upstream tests remain enabled.
Mesa RTTI follows the installed LLVM configuration. The native CLC embeds its
OpenCL headers even with shared LLVM so it remains usable after relocation.

The source must match the pinned Mesa archive and the applicable source patches:
the A733 BVNC addition and the shared Objective-C, GoogleTest and dynarray patches.
The target verifier also binds the shared dynarray header used by the generators.
The Objective-C patch keeps Objective-C enabled for macOS graphics consumers.
Generators without those consumers use only C and C++.

## Scripted build

The Python standard-library orchestrator uses SDK host API1:

~~~sh
"$HOST_PREFIX/bin/python3.15" -B scripts/build-mesa-generators.py \
    --sdk-source "$SDK_SOURCE" --host-prefix "$HOST_PREFIX" \
    --pkgdb "$HOST_PKGDB" --lock-directory "$LOCK_DIRECTORY" \
    --profile intel --jobs 4 /absolute/new-work /absolute/distdir
~~~

The work directory must be absent. A failed build retains its partial work.
The command checks the source archive checksum and uses existing native packages.
It does not install dependencies or modify the selected host prefix.
Set `LOCK_DIRECTORY` to the same SDK lock namespace as the package writer.
When the native LLVM C++ ABI uses an SDK binding, pass
`--native-cxx-binding-record /absolute/commands.json`; the common native
tool selector validates and uses its compiler adapters. The native LLVM and
CLC dependencies must use that same ABI. Without the option the selected
host toolchain retains its existing default route.

The producer holds shared leases for the prefix and package database until sealing finishes.
An active package writer prevents this read lease; no second installer is started.
The sealed result is in `WORK/sealed`.
Use the selected common cross toolchain and its matching target runtime for
subsequent target Mesa objects. To select the explicit GCC host alternative,
pass `--host-compiler-family gcc`; the default is `clang`.

## Seal and select capabilities

```sh
python3.15 seal-mesa-generators.py --sdk-source "$SDK_SOURCE" \
    --host-prefix "$HOST_PREFIX" --profile intel \
    --pkgdb "$HOST_PKGDB" --lock-directory "$LOCK_DIRECTORY" \
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
BMAKE=/absolute/native/bmake python3 ../tests/amd64-targets.py
BMAKE=/absolute/native/bmake python3 ../tests/amd64-targets.py \
    --distfiles /absolute/verified/distfiles
python3 ../tests/amd64-targets.py --skip-bmake \
    --distfiles /absolute/verified/distfiles
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

The native sealer records compiler argument directory paths separately from
regular file hashes. A directory path does not recursively bind every child file.
The copied generator smoke checks and shared-library checks are required before use.
Run the producer command regression without compiling fixture tools:

```sh
python3.15 ../tests/mesa-generator-producer.py --sdk-source /absolute/EmberBSD-SDK
```

The producer regression checks compiler routing, prefix-only discovery, RTTI,
assertions and test commands. It does not prove a native generator rebuild,
a target Mesa package or hardware rendering.
