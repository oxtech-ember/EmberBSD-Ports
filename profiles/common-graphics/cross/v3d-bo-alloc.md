# Bounded V3D buffer allocation probe

Use `v3d-bo-alloc.c` to measure allocation failures without a graphics session.
It opens `/dev/dri/renderD128` by default. An optional argument selects another render node.
It checks `DRM_IOCTL_VERSION` for the `v3d` driver before the allocation requests.
It then uses only `DRM_IOCTL_V3D_CREATE_BO` and `DRM_IOCTL_GEM_CLOSE`.
It does not map BOs, access MMIO, submit GPU jobs, or change driver limits.
A successful run proves allocation and handle release only. It does not prove GPU rendering.

The first phase creates and immediately closes each size:
4096, 1048576, 4194304, 5246976, 7475200, 8388608, 16777216, 16781312,
and 33554432 bytes. The last two requests test 16 MiB plus 4 KiB and 32 MiB.
Allocation failures do not stop the remaining size probes.
An explicit close failure stops further allocation and closes the descriptor.

The second phase retains two 5246976-byte BOs and one 7475200-byte BO.
This phase requests at most 17969152 live bytes, below 24 MiB.
The single and held phases do not overlap. The complete probe requests at most
33554432 live bytes (32 MiB), from one single-phase BO.
A failed held allocation stops that phase. All earlier handles are released in reverse order.
Every acquired descriptor receives one close attempt. Close errors are not retried.
Process exit releases residual file resources if an explicit release fails.
The kernel may allocate additional metadata or round the requested sizes.
The bound covers this probe, not the global GPU memory total.
Create/close does not exercise mmap, PRIME, or jobs and cannot prove absence of leaks.
Other allocations, fragmentation, or a kernel budget can affect large requests.
The fixed request count is bounded. A blocked kernel ioctl has no userspace timeout here.

Each line records the operation, requested size or handle, result, and errno.
Success lines report errno zero. A failed create does not expose its output handle as valid.
The CLI rejects a successful create with handle zero.
Exit status zero requires all allocations and releases to succeed.
An allocation, driver, close, or output error returns status one. Invalid argument count returns two.
`op=held` reports the successful handle count and the full planned request total.
Write stdout to a regular file; a closed output pipe can terminate the process with SIGPIPE.

## Cross-build

Use the common EmberBSD GCC16 compiler and its coherent EmberBSD sysroot.
Use `include/drm-uapi` from the pinned Mesa archive in [sources.tsv](../sources.tsv).
The probe needs the libc and DRM UAPI headers. It does not link libdrm or Mesa.
Use the same configured linker and GCC runtime search paths as the other cross probes.
For an already configured cross compiler:

```sh
"$CC" --sysroot="$SYSROOT" -std=c11 -O2 -g -Wall -Wextra -Werror \
    -I"$MESA_UAPI" v3d-bo-alloc.c -o v3d-bo-alloc
"$READELF" -h -d v3d-bo-alloc
```

On EmberBSD, run as the graphics-session user with access to the render node:

```sh
./v3d-bo-alloc /dev/dri/renderD128 > allocation.log
status=$?
printf 'status=%s\n' "$status"
```

Record the kernel revision, driver, memory conditions, and other GPU users.
A failed large request with successful small requests does not identify the cause.
It does not prove an allocation limit, contiguous-DMA failure, or fragmentation by itself.
The [process-local trace](v3d-bo-trace.md) measures actual application requests separately.

## Host contracts

```sh
../tests/v3d-bo-alloc.sh /absolute/new-output "$MESA_UAPI"
```

The runner compiles the production CLI as a separate translation unit.
Only its open, ioctl, and close adapters are replaced by the test.
It uses the real DRM UAPI structures and rejects every unexpected ioctl.
The test covers the exact sizes, flags, live-byte bound, driver rejection,
each create/close failure, invalid output handles, EINTR, and real output failure.
It checks cleanup of earlier held handles after a later allocation failure.
Normal and ASan/UBSan execution test those paths on the build host.
This does not emulate the kernel allocator or establish physical-device acceptance.
Run Cppcheck and GCC/Clang path analysis with the recorded compiler inputs.
If Valgrind is unavailable on the build host, record that limitation separately.
