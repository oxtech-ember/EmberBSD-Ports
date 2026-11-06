# POSIX PRIME imports

MesaLib 26.2.5nb2 separates the existing llvmpipe POSIX DMA-BUF import and
release path from Linux UDMABUF allocation. A native imported displaytarget
can use the exported descriptor's mmap operation. It does not need the
primary-only `MAP_DUMB` ioctl on its render descriptor. Linux allocation and
export code stays under its original guards. Failed displaytarget creation
releases the imported mapping and duplicate descriptor.

The KMS winsys initializes the map mutex for newly imported BOs. Both import
constructors check initialization and destroy the initialized mutex on later
construction failure. This does not change GEM-handle ownership or cached-BO
semantics.

The native kernel must implement DMA-BUF mmap for the intended exporter.
The NetBSD AMDGPU implementation that returns `ENODEV` needs its separate
OS TTM/UVM repair. This port does not create a Linux device, weaken descriptor
permissions, replace mappings or suppress a failed mmap operation.

## Prepare the actual-source regression

The preparer uses Python's standard library and an explicit source-regression
patch tool. It verifies the canonical archive and patch hashes. It extracts
only three known source files, applies the two focused patches with zero
fuzz, and emits the actual functions, layouts and enclosing platform guards.
It does not select a compiler, admit a tool into an SDK, or build Mesa.

```sh
"$PYTHON" -B tests/prepare-prime-import.py \
    /absolute/mesa-26.2.6.tar.xz /absolute/new-prime-work \
    --patch-tool /absolute/source-regression/patch
```

Run from this recipe directory. Select an accepted native GCC16 compiler to
execute the models on the build host, or cross-build them with the accepted
GCC16/sysroot and execute the outputs on EmberBSD. Never run a target ELF on
the build host. The two unused-warning exceptions cover model callbacks that
the unpatched platform guards intentionally exclude.

```sh
"$CC" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-parameter -Wno-unused-function \
    -I"$WORK/after" tests/prime-import.c -o "$WORK/after-check"
"$WORK/after-check" import
"$WORK/after-check" lock
```

Compile the same fixture with `-I"$WORK/before"` into `before-check`. Both
cases must return nonzero: the importer takes the opaque-file route, and
the KMS constructor uses a mutex that was not initialized. The patched cases
must succeed. Import tests cover duplicate, seek and mmap failures, unchanged
failure outputs, the DMA-BUF allocation type and balanced map/fd/heap release.
Lock tests cover successful publication, heap and mutex failures, failed size
discovery and failed plane construction for both import constructors.

These syscall and mutex models do not establish Mesa configuration, a complete
target build, kernel mapping, GEM-handle lifetime, cache coherency, hardware
rendering or a compositor session. They do not execute the full screen or
resource lifecycle. Complete normal packaging, native PRIME mapping, GBM/EGL
and compositor acceptance remain required. The upstream test suite is available
through the explicit `tests` package option. Run Cppcheck, applicable GCC
analysis and supported memory checks with the selected tools.
Source preparation alone is not a regression pass.

## Base libelf provider

On amd64, RadeonSI requires libelf. Mesa does not use a libelf package
buildlink. Its pre-configure guard checks the installed base marker against
the canonical elftoolchain `distinfo`, checks the installed public headers
against the base source manifest, requires `STN_UNDEF` in the generated
ELF definitions, and reads the shared library and archive
through the selected SDK ELF API. Cross mode requires an explicit target root.

Run the actual-source guard fixture and the production native/cross recipe
queries with the selected Python, SDK source and bmake:

```sh
"$PYTHON" -B tests/base-libelf-provider.py \
    --bmake /absolute/host/bmake \
    --sdk-source /absolute/selected-sdk-source \
    --work-parent /absolute/private-test-parent
```

The fixture exercises the checker with synthetic base headers and ELF files.
It checks distinfo and patch checksums, marker, header, machine, SONAME, alias,
archive, buildlink and SDK API refusals. It rejects missing or incorrect
`STN_UNDEF` values before Mesa configuration. Real bmake expands the native `/` root,
the cross `CROSS_DESTDIR` root and the AArch64 selection. This test does not
inspect an installed sysroot, configure Meson, build Mesa, or establish AMDGPU
runtime behavior.

## Native and cross shader generators

MesaLib 26.2.5nb3 uses upstream in-tree shader generators for native NetBSD
builds. The selected GCC16 compiles the C and C++ objects. Mesa then runs
`mesa_clc`, `vtn_bindgen2` and, on AArch64, `pco_clc` from that same build.
Both generator installation options are false. No generator enters the
Mesa package PLIST.

The native CLC library inputs are build-only dependencies: Clang 23.1.4,
SPIRV-Tools 2026.4nb1 and SPIRV-LLVM-Translator 23.1.2 or newer in the 23.1 family.
Clang supplies CLC libraries and resource headers. It is not the selected
C or C++ compiler. The `SPIRV-Tools` pkg-config interface uses the static
archive; its separately named shared interface is not selected. Mesa keeps
its ordinary shared LLVM dependency for llvmpipe and ORC.
Rusticl and Microsoft CLC stay disabled, so this selection does not require
libclc. The selected drivers remain enabled. Mesa's upstream test suite is
disabled by default; add `tests` to `PKG_OPTIONS.MesaLib` to build it and its
GoogleTest dependency. An explicit pkgsrc test phase requires this option.

The dependency floor rejects older Translator release families. Tools uses
its stable 2026.4 component release with the function-order repair. Headers
uses the matching stable vulkan-sdk-1.4.363.0 source. Neither recipe changes
the Vulkan SDK version for other packages. A source or make-metadata check
does not qualify this dependency closure.

Cross builds depend on the matching native `graphics/mesa-generators` package
and point Meson at its selected host-prefix tools. They do not acquire target
Clang or SPIRV dependencies. An explicitly supplied external seal keeps the
standalone verifier contract; normal package builds do not require a seal. See
the [cross generator workflow](../../../../profiles/common-graphics/cross/mesa-generators.md).

```sh
python3 -B tests/generator-modes.py --bmake /absolute/bmake \
    --work-parent /absolute/private-test-parent
```

This finite check parses the production recipe with real bmake for both
architectures. It keeps the local generator policy active. It replaces external
pkgsrc includes with records of the selected interfaces. It queries the
provider's package name/version through bmake, checks its shared source and
patch identity, exact version match, selected-Python substitution, generator
paths and external-seal branch, along with native/cross options and deliberate
selection/dependency faults. Switching generator modes refreshes a retained
native file; repeating the same selection preserves its timestamp. It does
not resolve the full pkgsrc dependency
graph, configure Meson, build a generator, or check the staged package. Full
native shader generation and package linkage/PLIST checks remain required. Run
the upstream test suite when the explicit
`PKG_OPTIONS.MesaLib+=tests` option is selected.

## Darwin generator language selection

`patch-meson.build-host-objc` selects Objective-C for Metal WSI and the
Darwin KosmicKrisp bridge. A generator build with empty `platforms` and
`vulkan-drivers` needs only C and C++. Default Darwin platform selection
and offscreen KosmicKrisp still require Objective-C. NetBSD configuration
and package output are unchanged; this host-only repair does not change
`PKGREVISION`.

From the Ports root, run the actual Meson configuration-fragment check:

```sh
"$HOST_PREFIX/bin/python3.15" -B -E profiles/common-graphics/tests/mesa-host-objc.py \
    /absolute/mesa-26.2.6.tar.xz "$HOST_PREFIX/bin/meson" \
    "$HOST_PREFIX/bin/nbpatch" /absolute/new-test-work
```

The check verifies the source archive and applies the shared patch with
zero fuzz. Nine cases retain upstream platform defaults, both Objective-C
consumers, NetBSD behavior and causal controls for the original language
and argument selection. Meson runs without a C or C++ compiler. Objective-C
consumers must reject an explicitly absent compiler. Complete generator
builds and target rendering remain separate checks.

## Staged dynamic ELF compatibility

The native and cross recipes require an explicit SDK source on both CPUs.
Before configuration, `check-dynamic-elf.py --check-sdk` requires the SDK's
`ELF_RELOCATIONS_API=1`, dynamic ELF readers and stable-file APIs. The existing
amd64 base-libelf guard remains separate and unchanged.

The mandatory `post-install` hook reads `${DESTDIR}${PREFIX}/lib` before the
staged package is published or installed. It reads every regular ELF file,
including files below driver directories. ELF64 little-endian, `ET_DYN` and
the selected CPU are required. A regular `*.so*` file without ELF magic is
an error. An empty ELF set is also an error.

NetBSD x86_64 rejects dynamic relocation types 34, 35 and 36, and the
`DT_TLSDESC_PLT` and `DT_TLSDESC_GOT` tags, including zero-valued tags.
The SDK reads actual REL, RELA and JMPREL tables without section headers.
AArch64 does not receive the x86 policy. This gate detects a known loader
incompatibility. It does not qualify all relocations, TLS execution or runtime
admission. Rendering and compositor acceptance remain separate checks.

Symlink aliases are skipped, not opened as ELF files. Directory symlinks
are not traversed; an escaped directory symlink is an error. The selected
library directory must have no symlink ancestors. PLIST, alias closure and
package-lifecycle checks remain required. Keep the staging tree unchanged
while the checker runs. SDK identity checks cover all reads and each hash.

The checker writes JSON to stdout. Each library record contains its relative
path, SHA256 and the SDK's relocation scan. It never executes target code or
changes the package. Both hooks use the selected Python with `-B -E -S`.

```sh
"$PYTHON" -B -E -S tests/dynamic-elf.py \
    --sdk-source /absolute/selected-sdk-source \
    --bmake /absolute/selected-bmake --work-parent /absolute/private-test-parent
```

The regression uses raw-byte ELF fixtures and the actual checker. It covers
compatible old TLS, every forbidden type in all three table kinds, both tags,
AArch64 preservation, malformed/wrong-CPU/wrong-type files, damaged DSO magic,
empty inputs, aliases, directory escape and missing SDK capabilities.
Causal controls remove only the forbidden-type policy and change bytes between
relocation parsing and hashing. Real bmake dry-runs both recipe hooks for each
CPU in native and cross modes. External dependency includes are outside this
finite source check. No compiler, configure step, generator or target program
runs. These fixtures do not establish a complete package or installed runtime.

## Unordered array deletion

`dynarray-delete.c` exercises the prepared Mesa `u_dynarray.h`: deletion of
last and interior elements, a missing value, and a subsequent last element.
Its local copy observer rejects self-copy even on hosts whose libc does not.
Compile it with the selected host compiler and the prepared patched Mesa
`src/util` include directory, then run it. For example:

```sh
"$HOST_CC" -std=c11 -Wall -Wextra -Werror -I"$MESA_SOURCE/src/util" \
    dynarray-delete.c -o "$WORK/dynarray-delete"
"$WORK/dynarray-delete"
```

The original header returns 1 on the first case; the patched header returns 0.
This fixture checks array behavior and overlap, not the full NIR compiler or
target libc. The affected Mesa test binaries still require target execution.

## PowerVR submit interruption

Run the focused host regression against the Mesa source after applying the
recipe patches. Select Clang and its matching `ld.lld` from the native prefix:

```sh
"$PYTHON" -B tests/pvr-submit-contract.py \
    --mesa /absolute/patched-mesa-source \
    --cc /absolute/native-prefix/bin/clang \
    --work-parent /absolute/private-test-parent
```

The test compiles the actual bounded Mesa submit helper and driver queue
function with a fake ioctl and sync callbacks. It checks a completed job
followed by an interrupted wait, no replay or tail signal, terminal NetBSD
queue loss, successful submission and unchanged Linux retry/error behavior.
ASan and UBSan instrument the fixture. The test models the kernel interface;
it does not build the Vulkan driver or execute work on a GPU.

## Standalone cross LLVM routing

The common Mesa recipe selects the target LLVM metadata helper through the
normal cross configuration, including a validated explicit override. Full
Mesa checks target metadata at configure time; `softpipe-only` does not select
the helper. Run `standalone-llvm-route.py --pkgsrc PKGSRC --makeconf MAKECONF
--bmake BMAKE` to check the real pkgsrc metadata and refusal contracts. This
check does not build Mesa or establish graphics runtime support.

## GE8300 transfers and D24 background depth

`pvr-buffer-copy.c` checks aligned buffer copies and fills on the selected
GE8300 Vulkan ICD. Build it with the selected target Clang and Vulkan loader.
Run these cases on the target:

```sh
./pvr-buffer-copy 48 48
./pvr-buffer-copy 64 64
./pvr-buffer-copy 44 44
./pvr-buffer-copy 80 80
./pvr-buffer-copy 12 12 --fill
./pvr-buffer-copy 20 20 --fill
```

Each case checks all 256 bytes in both buffers, including guards. The original
ICD passes a 64-byte copy and a 48-byte copy split with `48 32`. A single
48-byte copy resets its SIPFv1 transfer context. Stop after a device error;
do not repeat work on a failed GPU. The fix splits aligned odd one-row
transfers into normal GPU TQ commands. It does not change byte-sized or
unaligned transfers, or qualify every FAST_2D operation.

`pvr-depth.c` checks D24S8 background clears and depth writes with `LESS`.
Four scissors select z values `0`, `.25`, `.75`, and `1`. A later, farther
cyan triangle must fail after each accepted depth write. The oracle checks
every color byte, row padding, tail padding, and guard byte.

Generate shader headers with the native Ports tool, then cross-build:

```sh
"$HOST_PREFIX/bin/glslangValidator" -V --target-env vulkan1.2 \
    --vn depth_vertex -o "$WORK/depth-vertex.h" pvr-depth.vert
"$HOST_PREFIX/bin/glslangValidator" -V --target-env vulkan1.2 \
    --vn depth_fragment -o "$WORK/depth-fragment.h" pvr-depth.frag
printf '%s\n' '#include <stdint.h>' '#include "depth-vertex.h"' \
    '#include "depth-fragment.h"' > "$WORK/depth-shaders.h"
"$TARGET_CC" -std=c11 -O2 -Wall -Wextra -Werror -I"$WORK" \
    -I"$TARGET_SYSROOT/usr/pkg/include" pvr-depth.c \
    -L"$TARGET_SYSROOT/usr/pkg/lib" -Wl,-rpath,/usr/pkg/lib -lvulkan \
    -o "$WORK/pvr-depth"
```

Select the target ICD through `VK_DRIVER_FILES`. Run `pvr-depth 0`,
`pvr-depth .5`, and `pvr-depth 1` on the target. Expected colored regions are
zero, two, and three; z=1 always fails `LESS`. Before the fix, clears `.5`
and `1` fail the oracle while clear `0` passes. All three pass with the fix.
The capability is enabled only in the GE8300 22.102.54.38 hardware table.
Other device tables retain their existing D24 encoding. This regression
does not qualify D16 or other GPU models.

On a warm YS-M33/A133, these cases and a Qt 6.12 Vulkan offscreen frame passed
with hardware depth enabled. The Qt oracle compared all 1280x800 RGBA pixels.
This evidence does not qualify a complete Qt application or device image.

## GLSL numeric locale regression

The common Mesa conversion uses the probed locale-specific functions with an
explicit C numeric locale. This keeps decimal GLSL literals independent of the
application's `LC_NUMERIC`. The Mesa source path below must already contain the
normal recipe's complete patch set; do not modify an active build tree.

For a NetBSD target, select the SDK target compiler and its sysroot through
`CC` and its normal configuration. From the Ports root, compile the actual
patched `strtod.c` with the standalone regression:

```sh
"$CC" -std=c11 -O2 -DHAVE_STRTOD_L -DHAVE_STRTOF -DHAVE_PTHREAD \
    -DHAVE_STRUCT_TIMESPEC -DUSE_GCC_ATOMIC_BUILTINS \
    -I"$MESA_SOURCE/src" -I"$MESA_SOURCE/src/util" -I"$MESA_SOURCE/include" \
    -pthread "$MESA_SOURCE/src/util/strtod.c" \
    profiles/common-graphics/tests/mesa-strtod-locale.c -o "$TEST_BINARY"
```

Run the resulting target executable on the target with an installed comma
locale, for example `"$TEST_BINARY" ru_RU.UTF-8`. It refuses a missing or
non-comma locale and checks values and end pointers after comma → C → comma
transitions. The first conversion runs in the comma locale so the test covers
locale-object creation, not only a later locale change. Compile the old source
and a control with only the feature-guard change to distinguish both causes.

For the actual graphics consumer, build `cross/mesa-render.c` with the normal
selected EGL/GL/GBM package inputs and run on the target with shader caching
disabled, e.g.:

```sh
EMBER_MESA_TEST_LOCALE=ru_RU.UTF-8 MESA_SHADER_CACHE_DISABLE=true \
    "$MESA_RENDER" "$RENDER_NODE" "$EXPECTED_RENDERER"
```

The diagnostic refuses a missing or non-comma locale, checks the renderer and
reads back the GLSL fractional color alongside its existing triangle checks.
Run a separate C-locale control. A matching image tests the selected renderer;
it does not by itself establish installation, package lifecycle or compositor
acceptance.

## Native cached BOs

Prepare Mesa with the complete current recipe patch set. Run the actual-source
CREATE_BO regression with the selected native SDK compiler:

```sh
"$PYTHON" tests/pvr-cached-bo-contract.py --mesa "$MESA_SOURCE" \
    --cc "$HOST_CC" --work-parent "$WORK"
```

The fake ioctl rejects bit 63 as an older kernel would. It checks the complete
`0x8000000000000004` request, unchanged output on refusal, a capable kernel,
and ordinary coherent allocation. The previous 32-bit helper fails this test.

Cross-build `pvr-buffer-copy.c` against the target Vulkan loader. On the running
native render driver, select the PowerVR ICD and run:

```sh
./pvr-buffer-copy 192 192 --cached
```

This selects HOST_CACHED memory, flushes CPU writes, submits a GPU copy, waits
for its fence, invalidates GPU writes, and checks all bytes and guard regions.
Without `--cached`, the original coherent check remains unchanged. `--fill`
selects a GPU fill instead of a copy. Do not reinitialize a running GPU.

On one A133/GE8300 the cached copy passed with memory type 1, flags `0xb`, and
`drm_failed=0`. Host CREATE_BO models and a native device copy are distinct checks.
PRIME, compositor operation and sustained application frame rate remain separate.

Clang analysis of the three changed Mesa translation units reported only the
unchanged `MapMemory2` size assignment when `NDEBUG` removes its assertion.
Cppcheck 2.22.0 also reported unchanged upstream paths: the scalar `nir_channel`
call into `nir_swizzle`, and the `UNREACHABLE` allocator fallback in `pvr_gpu_upload`.
Neither finding identifies a new cache path error. The kernel's actual-source BO
model passed Cppcheck, Clang analysis, ASan and UBSan for both native page sizes.
Valgrind was unavailable in the selected SDK; no Valgrind result is claimed.
