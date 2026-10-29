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
    /absolute/mesa-26.2.5.tar.xz "$HOST_PREFIX/bin/meson" \
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
