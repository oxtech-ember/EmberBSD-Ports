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
    /absolute/mesa-26.2.5.tar.xz /absolute/new-prime-work \
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
resource lifecycle. Complete normal packaging, upstream tests, native PRIME
mapping, GBM/EGL and compositor acceptance remain required. Run Cppcheck,
applicable GCC analysis and supported memory checks with the selected tools.
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
libclc. Drivers and upstream tests stay enabled.

The dependency floor rejects older Translator release families. Tools uses
its stable 2026.4 component release with the function-order repair. Headers
uses the matching stable vulkan-sdk-1.4.363.0 source. Neither recipe changes
the Vulkan SDK version for other packages. A source or make-metadata check
does not qualify this dependency closure.

Cross builds retain the existing sealed build-host generators and native
Meson file. They do not acquire target Clang or SPIRV dependencies. See the
[cross generator workflow](../../../../profiles/common-graphics/cross/mesa-generators.md).

```sh
python3 -B tests/generator-modes.py --bmake /absolute/bmake \
    --work-parent /absolute/private-test-parent
```

This finite check parses the production recipe with real bmake for both
architectures. It keeps the local generator policy active. It replaces external
pkgsrc includes with records of the selected interfaces. It checks native and
cross options, build-only dependency methods, generator installation, missing
cross seals, and deliberate selection/dependency faults. It does not resolve
the full pkgsrc dependency graph, configure Meson, build a generator, or check
the staged package. Full native shader generation, upstream tests and package
linkage/PLIST checks remain required.
