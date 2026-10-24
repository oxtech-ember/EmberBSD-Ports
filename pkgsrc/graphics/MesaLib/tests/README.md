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
