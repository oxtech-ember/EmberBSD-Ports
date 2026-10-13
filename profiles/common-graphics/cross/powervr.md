# PowerVR Vulkan ICD through the common Mesa package

The optional `powervr` pkgsrc option adds the upstream Imagination Vulkan
ICD to MesaLib 26.2.4nb5. It retains V3D, VirGL, softpipe, llvmpipe,
X11, Wayland, EGL, GBM and the shared LLVM 23.1.3 provider.
The installed Vulkan loader now enumerates the physical GPU on Zero 3W.
The normal package and bounded enumeration checks pass. GPU submission
and accelerated Plasma remain unaccepted.

This is a native PowerVR DRM consumer. It has no diagnostic-packet backend.
The OS owns render-node identity, GEM buffers, GPU page tables and syncobj.
`vkCreateDevice`, context creation, queue submission, GPU cache ownership,
PRIME presentation and Plasma are separate acceptance steps.

## Native build tools

Use the [upstream Mesa host-tool build](../../../probes/a733-accelerators/host-tools/README.md)
with the pinned Mesa 26.2.4 archive, LLVM 23.1.3 and current SPIR-V dependencies.
Apply its maintained SPIRV-Tools function-order fix. Relink `mesa_clc` after
that static dependency changes. An older installed `mesa_clc` can differ from
the corrected executable in the actual build directory.

Seal the three executables from that real build:

```sh
TMPDIR=/absolute/external/tmp ruby seal-mesa-generators.rb \
    /absolute/mesa-26.2.4.tar.xz /absolute/native-mesa-source \
    /absolute/native-mesa-build /absolute/spirv-val /absolute/new-generators
```

The helper currently supports macOS ARM64 host tools. It checks the archive
SHA256, the full pinned source file set and the selected build's metadata.
The optional exact-BVNC CLI patch is the only accepted native source delta.
The helper copies `mesa_clc`, `vtn_bindgen2` and `pco_clc` from their build
outputs. It rejects non-system shared-library dependencies for those tools.
It records the actual compilers, link libraries, command metadata and inputs.

The helper discovers dependencies with the actual compiler depfile. It hashes
source, generated and implicit Clang headers before the accepted compile.
It rejects changed dependency sets or bytes. The two virtual OpenCL built-ins
are bound to their generated embedded arrays and the real static-header flag.
The helper compiles all three upstream common OpenCL inputs. It validates the
resulting SPIR-V, generates NIR and generates the common USC programs.
It retains upstream assertions and `PCO_DEBUG=no_pred_cf` for precompilation.
It adds no diagnostic shader. This is build-host execution, not a GPU test.
Sealing verifies existing compiled tools; it does not claim a fresh native rebuild.

`installed.sha256` binds the tool bytes and receipt. `interface.sha256` binds
the target NIR, PCO and common-shader interfaces to the same source revision.
The recipe checks both manifests before configuring Mesa. The receipt is a
local build provenance record; it is not a signature or an upstream attestation.

## Normal cross package

Prepare a fresh `common-graphics` export and use the existing
[graphics cross configuration](profile.md). Add these settings to the
private MAKECONF after its common profile:

```make
PKG_OPTIONS.MesaLib+= powervr
EMBERBSD_MESA_GENERATORS=/absolute/new-generators
```

Run the ordinary pkgsrc `package` target in `graphics/MesaLib`. Use a fresh
WRKOBJDIR and a separate package output directory. Do not overwrite another
build's work tree or install into a shared sysroot during the candidate build.
The package must pass normal staging, PLIST, ELF ABI and work-reference checks.
The option adds these installed files:

- `/usr/pkg/lib/libvulkan_powervr_mesa.so`
- `/usr/pkg/share/drirc.d/00-pvr-defaults.conf`
- `/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json`

The recipe supplies the host tools through a native Meson file.
Target libraries still use the common cross file and target sysroot.
`-Dmesa-clc=system` and `-Dprecomp-compiler=system` prevent execution of target
compiler programs on the build host. No target SPIRV-Tools or translator
runtime is required for this path. Upstream Python generators still run with
the common build-host Python 3.14.

The source patches use Mesa's existing device-number header checks on BSD.
PowerVR UAPI types come from Mesa's platform-aware DRM header. Portable
64-bit flag constants preserve the ioctl ABI. Wayland presentation uses
RAW clocks only when the target defines them; monotonic timing is retained.
The IDFWDF shared header reserves all four sampler words before its address.
The runtime and generated common shader consume this identical header.
The source-causal ABI proof remains in the
[IDFWDF owner](../../../probes/a733-accelerators/host-tools/README.md).

## Installed enumeration

First prepare the native OS driver. The current board kernel acceptance uses
EmberBSD `f46cd40a5f28`. Its ordinary DTB starts in observe-only mode.
Follow the OS [render-node procedure](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-pvr-render.md),
including firmware stage 13 before registration. The
[query contract](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-pvr-queries.md)
and [syncobj contract](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/drm-syncobj.md)
are required dependencies. Package installation alone does not activate them.

Use the canonical `vulkan-loader` and `vulkan-headers` packages.
The current shared target sysroot supplies 1.4.357.0, with loader revision nb2.
Build the small consumer against that installed loader:

```sh
ruby build-powervr-enumeration.rb /absolute/common-cross-tools \
    /absolute/ember-sysroot /absolute/new-enumeration-check
```

After normal candidate package installation on the selected board, transfer
that consumer and runner. Use the native PowerVR render node:

```sh
PVR_I_WANT_A_BROKEN_VULKAN_DRIVER=1 sh run-powervr-enumeration.sh \
    /dev/dri/renderD128 /absolute/new-result
```

This is the upstream experimental opt-in. Mesa 26.2.4's conformant-device
check does not include BXM 36.56.104.183. The recipe does not remove that gate
or set the opt-in for ordinary users. A successful check does not establish
Vulkan conformance.

The consumer creates and destroys four instances. It requires one PowerVR
physical device with the expected vendor, driver ID and render-node numbers.
Mesa also creates a VM and three static BO mappings during enumeration.
The consumer never creates a Vulkan device or submits a queue.
The runner records the kernel, installed packages, ICD and loader closure.
It selects only the installed PowerVR manifest and uses normal library lookup.

## Physical acceptance

On 2026-10-13, the 4 GiB Orange Pi Zero 3W passed with kernel
`f46cd40a5f28` (`EMBER64 #13`, GCC 16.2), including the current USB series.
The PCB revision was not recorded. Firmware remained `1.1.6976702` for
BVNC `36.56.104.183`. The package source was Ports `95ea6b4`.
MesaLib 26.2.4nb5, libdrm 2.4.134nb2 and vulkan-loader 1.4.357.0nb2
used their installed canonical libraries. Normal package upgrade and all
98 Mesa payload-file checks passed.

Four instances reported `PowerVR B-Series BXM-4-64 MC1`, Vulkan `1.2.354`,
and the actual render node `180:128`. The loop completed in about one second.
Upstream still warns that core-count fetching is unimplemented and uses one.
The `MC1` label therefore does not measure the physical core count.
The experimental conformance warning remains visible.

The same package passed four 16x16 shader/pixel/EGL cycles with llvmpipe,
LLVM 23.1.3, EGL 1.5 and GLES 3.2. All 38 target invocations exited zero
in 65 seconds. `Cache.List` remained skipped; nine NIR cases remained disabled.
All nine host tests passed, including the new PowerVR symbol check.
The GL check reports the missing Zink driver before selecting llvmpipe.
It establishes CPU-rendering regression coverage, not PowerVR rendering.

## Checks and limits

The actual consumer has an ASan/UBSan fixture for success, API failure,
empty/incomplete arrays, unsupported properties and wrong device identity.
A causal mutant that omits the render-node check must fail this fixture.
The receipt regression uses the production verifier and rejects changed
binaries, missing entries, duplicate tools, unsafe paths and ABI mismatches.
It also checks the final manifest row when that row has no trailing newline.
Run it with the real sealed native tools:

```sh
ruby ../tests/mesa-generators.rb /absolute/digest \
    /absolute/sealed-generators /absolute/new-receipt-tests
SANITIZERS=yes sh ../tests/powervr-enumeration.sh \
    /absolute/vulkan-header-prefix /absolute/new-consumer-tests
```

Test actual pkgsrc option selection with the same recorded host inputs:

```sh
BMAKE=/absolute/bmake DIGEST=/absolute/digest \
    ruby ../tests/powervr-selection.rb /absolute/prepared-pkgsrc \
    /absolute/common-mk.conf /absolute/llvm-config /absolute/wayland-scanner \
    /absolute/sealed-generators /absolute/patched-mesa-source \
    /absolute/new-selection-tests
```

This parses the real recipe, writes its native Meson file and runs its
production receipt check. It verifies that the default GL option is unchanged.
The WSI regression extracts both clock conversions and the presentation
admission expression. It runs with and without the RAW clock feature.
The UAPI check compares target structure layouts, flags and ioctl encodings
against an explicit constant-expression model. It also requires the original
BSD header to fail on its Linux-only include. The model is not a Linux build.

```sh
SANITIZERS=yes ruby ../tests/wayland-clock.rb \
    /absolute/patched-mesa-source /absolute/new-clock-tests
ruby ../tests/powervr-uapi.rb /absolute/upstream-mesa-source \
    /absolute/patched-mesa-source /absolute/cross-gcc /absolute/ember-sysroot \
    /absolute/new-uapi-tests
```

Host models do not replace installed loader/ICD acceptance.
Valgrind is not supported on the macOS ARM64 build host; ASan/UBSan is a separate memory check.
Analyze the actual target PowerVR translation units after clean configuration
creates their generated headers. Compare the pinned and patched source with
the same target compilation arguments and record analyzer limitations.

Cppcheck 2.22 covered 59 target translation units; 52 upstream baselines
preprocessed successfully. Comparable error/warning signatures did not change.
GCC 16.2 and Clang 22.1.8 covered seven selected units. Original portability
failures and analyzer path limits remain explicit. This is not a clean audit
of the entire driver. Ports and Mesa upstream own the retained debug-disassembler
OOM findings and unclosed graphics/transfer diagnostics. Those paths need
regressions before their later execution acceptance.
