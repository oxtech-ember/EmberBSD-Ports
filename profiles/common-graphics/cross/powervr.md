# PowerVR Vulkan ICD through the common Mesa package

The default AArch64 MesaLib package contains the upstream Imagination Vulkan
ICD. MesaLib 26.2.4nb5 added it. The default package includes it without an option.
MesaLib 26.2.5 contains the upstream PCO fix for the workgroup barrier
race when a loop uses the barrier again. The BVNC and IDFWDF patches
apply to 26.2.5 without changes.
From 26.2.5nb1, the same package also contains the V3D Vulkan ICD
(`lib/libvulkan_broadcom.so` and `share/vulkan/icd.d/broadcom_icd.json`).
The package retains V3D, VirGL, softpipe, llvmpipe,
X11, Wayland, EGL, GBM and the shared LLVM provider.
The explicit `softpipe-only` option omits Vulkan ICDs. From 26.2.6nb14,
add `powervr` to this small set for the PowerVR ICD without target LLVM:

```make
PKG_OPTIONS.MesaLib+= softpipe-only powervr -llvm -wayland
```

This selection keeps softpipe, X11, EGL, GLES and GBM. It adds the Vulkan
loader and PowerVR files. It requires an AArch64 cross build and the sealed
`powervr` host generators described below. Native builds and other target
architectures reject this option. The default full graphics set is unchanged.
The installed Vulkan loader now enumerates the physical GPU on Zero 3W.
The normal package and bounded enumeration checks pass. Native compute also passes
on the accepted EmberBSD kernel. Graphics and accelerated Plasma remain unaccepted on Zero 3W.

GE8300 (BVNC 22.102.54.38, Allwinner A133) uses simple parameter format
version 1, and upstream Mesa builds render targets only for version 2.
From 26.2.6nb13, two patches remove the version 2 assumptions (2x2 tile
groups and the 16-macrotile layout). A third encodes the PPP terminate clip
in tiles; 32-pixel blocks left three quarters of each render unprocessed.
GE8300 graphics need EmberBSD
[OS 99a54c18](https://github.com/oxtech-ember/EmberBSD/commit/99a54c183795)
or later; older kernels reject GE8300 render work. With that kernel on an
A133 tablet, offscreen Vulkan triangles at 256x256, 1280x800, 256x64 and
64x256 were pixel-exact. The `softpipe-only powervr` cross package
builds with Clang and no target LLVM. Its ICD passed these cases on one
warm-booted A133, including row padding and buffer guards.

From nb15, aligned odd one-row SIPFv1 transfers of 32- or 128-bit texels
use split normal GPU TQ commands. FAST_2D could reset the transfer context.
The GE8300 22.102.54.38 device table also selects floating-point D24
background-depth register encoding. Other device tables keep the existing
encoding. The [causal regressions](../../../pkgsrc/graphics/MesaLib/tests/README.md#ge8300-transfers-and-d24-background-depth)
cover buffer guards and D24 clears at 0, .5 and 1 with depth writes.

On that warm A133, Qt 6.12 rendered a four-rectangle frame through Vulkan
with its normal opaque/depth path. All 1280x800 RGBA pixels matched.
The GPU readback also reached the bsdfb raster backing store. This checks
one controlled frame, not a complete application or sustained performance.
The default full package and multisampling were not tested.

This is a native PowerVR DRM consumer. It has no diagnostic-packet backend.
The OS owns render-node identity, GEM buffers, GPU page tables and syncobj.
The bounded compute check covers device creation, submission and host readback.
Application graphics, PRIME presentation and Plasma require separate acceptance.

## Native cached readback

From 26.2.6nb17, AArch64 can expose a second memory type with `HOST_CACHED`
and without `HOST_COHERENT`. Mesa requests the native EmberBSD cached BO flag
with all 64 bits preserved. A failed probe retains the original coherent type.
Older kernels therefore keep their existing behavior.

Flush and invalidate use Mesa's shared cache helpers. The reported
`nonCoherentAtomSize` uses their writeback granularity. The kernel and userspace
must support the same non-coherent ownership protocol. External memory and
scanout allocations retain the coherent type; cached PRIME export is rejected.
Heterogeneous CPU cache-granularity handling remains unqualified on EmberBSD.

On one A133/GE8300, a 4,096,000-byte CPU copy fell from 41.8 ms to 3.25–3.28 ms
after initial mapping faults. A cached Vulkan GPU copy preserved exact bytes
and both buffer guards. These checks do not establish direct scanout or frame rate.
See the [cached BO checks](../../../pkgsrc/graphics/MesaLib/tests/README.md#native-cached-bos).

## Native build tools

Normal Mesa cross package builds obtain the host tools from
`graphics/mesa-generators` through `TOOL_DEPENDS`. Use the
[standalone sealed generator workflow](mesa-generators.md#explicit-external-tool-directory)
only when a consumer needs tools outside the package graph. That workflow
supports Linux x86_64 with Clang and macOS ARM64 with Clang or the explicit GCC
alternative; select `--profile powervr` or `--profile all`.

That owner documents the compiler selection, current versions, native build,
shader checks and sealing. It supplies `mesa_clc`, `vtn_bindgen2` and `pco_clc`
from one compatible source and host ABI. Rebuild affected generators after
a dependency ABI changes; retain compatible objects. Host code generation
does not establish GPU execution.

## Normal cross package

Prepare a fresh `common-graphics` export and use the existing
[graphics cross configuration](profile.md). No generator path setting is
needed for the ordinary package dependency path.

Run the ordinary pkgsrc `package` target in `graphics/MesaLib`. Use an owned
WRKOBJDIR and a separate package output directory. Retain compatible objects.
Do not overwrite another build's work tree or install into a shared sysroot
during the candidate build.
The package must pass normal staging, PLIST, ELF ABI and work-reference checks.
The AArch64 package installs these PowerVR files:

- `/usr/pkg/lib/libvulkan_powervr_mesa.so`
- `/usr/pkg/share/drirc.d/00-pvr-defaults.conf`
- `/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json`

The recipe supplies the host tools through a native Meson file.
Target libraries still use the common cross file and target sysroot.
`-Dmesa-clc=system` and `-Dprecomp-compiler=system` prevent execution of target
compiler programs on the build host. No target SPIRV-Tools or translator
runtime is required for this path. Upstream Python generators still run with
the selected build-host Python 3.15.

The source patches use Mesa's existing device-number header checks on BSD.
PowerVR UAPI types come from Mesa's platform-aware DRM header. Portable
64-bit flag constants preserve the ioctl ABI. Wayland presentation uses
RAW clocks only when the target defines them; monotonic timing is retained.
The IDFWDF shared header reserves all four sampler words before its address.
The runtime and generated common shader consume this identical header.
The source-causal ABI proof remains in the
[IDFWDF owner](../../../probes/powervr/host-tools/README.md).

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

## Compute consumer and Zink build

MesaLib 26.2.4nb6 adds Zink to the common GL driver selection.
The AArch64 cross package builds with the same common GCC16 and LLVM toolchain.
This package build does not establish Zink execution on PowerVR.
The physical results below apply to the earlier nb5 package.

The compute consumer requires the OS [native execution path](https://github.com/oxtech-ember/EmberBSD/blob/main/ember/boot/a733-pvr-execution.md).
Complete its explicit firmware preparation and execution activation first.
Build the consumer and validate its SPIR-V with the recorded host tools:

```sh
ruby build-powervr-compute.rb /absolute/common-cross-tools \
    /absolute/ember-sysroot /absolute/spirv-tools-prefix /absolute/new-compute-check
```

Transfer the built consumer and runner from that output directory.
After installing the reviewed Mesa package, run:

```sh
PVR_I_WANT_A_BROKEN_VULKAN_DRIVER=1 sh run-powervr-compute.sh \
    /dev/dri/renderD128 /absolute/new-compute-result
```

The consumer requires the actual PowerVR render node and Mesa driver identity.
It creates a Vulkan device, submits one compute shader, and waits for its fence.
It checks sixteen output words against `0x13579bdf XOR index`.
It applies the required buffer barriers and host flush/invalidate operations.
The fence wait is bounded. Failed submitted work does not trigger unsafe user cleanup.
The runner records package identities and the normal loader closure.
On Zero 3W, kernel `4d9b68f3ec4866ad46810b4257daf4333ef10f38` passed three
compute cycles with this installed nb5 package. All sixteen words matched.
The 155 samples across installation and functional checks peaked at 62.310 degrees Celsius.
The PLL and compute checks peaked at 61.938 degrees Celsius; the stop limit was 80.
See the [OS acceptance boundary](https://github.com/oxtech-ember/EmberBSD/blob/c73b1ade9b76a4ede3fa8b64d69b8f118f21f38d/ember/boot/a733-pvr-execution.md).
The separate [offscreen graphics consumer](powervr-offscreen.md) remains unaccepted on hardware.

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
The host-policy regression accepts the supported Darwin and Linux pairs, rejects
wrong CPU/compiler pairs, and rejects compiler or inspector paths outside the
selected prefix:

```sh
python3.15 ../tests/mesa-generators-host.py ../cross/mesa_generator_host.py
```

Run it with the real sealed native tools:

```sh
python3.15 ../tests/mesa-generators.py --sdk-source "$SDK_SOURCE" /absolute/digest \
    /absolute/sealed-generators /absolute/new-receipt-tests
SANITIZERS=yes sh ../tests/powervr-enumeration.sh \
    /absolute/vulkan-header-prefix /absolute/new-consumer-tests
```

Test actual pkgsrc selection with the same recorded host inputs:

```sh
BMAKE=/absolute/bmake DIGEST=/absolute/digest \
    ruby ../tests/powervr-selection.rb /absolute/prepared-pkgsrc \
    /absolute/common-mk.conf /absolute/llvm-config /absolute/wayland-scanner \
    /absolute/sealed-generators /absolute/patched-mesa-source \
    /absolute/new-selection-tests
```

This parses the real recipe, writes its native Meson file and runs its
production receipt check. It verifies that the default AArch64 selection
contains PowerVR and advertises the optional small graphics selection.
The recipe's `tests/generator-modes.py` also checks that the small selection
omits target LLVM and rejects unsupported native and architecture choices.
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
