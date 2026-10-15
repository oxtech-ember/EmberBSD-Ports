# V3D buffer allocation trace

Use this opt-in diagnostic when KWin discovers V3D but Mesa cannot allocate a buffer.
It does not change a package, select a render node, or alter driver limits.
It does not establish Plasma, HDMI, or KMS acceptance.

`v3d-bo-trace.c` wraps the public libdrm `drmIoctl(int, unsigned long, void *)` entry point.
Mesa 26.2.4 `src/gallium/drivers/v3d/v3d_bufmgr.c` calls `v3d_ioctl` for buffer allocation and GEM close.
`src/broadcom/common/v3d_util.h` forwards this call to `drmIoctl` outside simulator builds.
Use the pinned Mesa and libdrm archives from [sources.tsv](../sources.tsv).
Use `v3d_drm.h` from that Mesa archive and the matching libdrm headers.

The wrapper forwards each call once with its original descriptor, request, and pointer.
It restores the incoming errno before the provider call and preserves the returned errno.
Only `DRM_IOCTL_V3D_CREATE_BO` and `DRM_IOCTL_GEM_CLOSE` produce trace lines.
The requested size is captured before the call. A successful allocation also records the returned handle.
A private pipe copies each fixed-size UAPI structure through the kernel.
An inaccessible pointer produces `input=unreadable`; its printed zero fields are unknown values.
Failed calls have `output=unavailable`; their printed handle is not a returned handle.
Use `ret` to identify success. On success, errno can retain an earlier value.

The diagnostic adds timing and system-call overhead. Do not use it for performance measurements.
Write stderr to a regular file. A closed pipe can deliver SIGPIPE to the process.
If the next `drmIoctl` symbol cannot be resolved, the process exits with status 125.

## Build and verify

Cross-compile the shared object with the common EmberBSD GCC16 toolchain, its sysroot, and LLD configuration.
Add `-std=c11 -O2 -g -Wall -Wextra -Werror -fPIC -shared -pthread`.
Add include paths for target `usr/pkg/include`, `usr/pkg/include/libdrm`, and Mesa `include/drm-uapi`.
The shared object resolves libdrm with `dlsym(RTLD_NEXT, "drmIoctl")`; do not link a replacement ioctl implementation.
Cross-compile [v3d-bo-trace-smoke.c](../tests/v3d-bo-trace-smoke.c) with the same headers and link `-ldrm`.
Inspect both ELF files, their runtime dependencies, and the exported `drmIoctl` symbol.

Run [v3d-bo-trace.sh](../tests/v3d-bo-trace.sh) on the build host.
Pass a new output directory, pristine libdrm headers, and the Mesa UAPI directory.
On macOS, use pristine `xf86drm.h`, `drm.h`, and `drm_mode.h`; the target configured header requires target atomic definitions.
The test executes the real wrapper with only the resolver and provider replaced.
It checks pointer identity, one call per request, output mutation, original size, errno, bad pointers, and a failed log write.
ASan/UBSan covers the executable contract with valid pointers and NULL.
The normal contract also covers a deliberately unreadable pointer.
ASan intercepts `write` before kernel validation, so that case cannot use the sanitizer path.
This is not Valgrind Memcheck. Record the host platform limitation when Memcheck is unavailable.
Run Cppcheck and a path analyzer with the actual headers and target definitions.

On EmberBSD, run the smoke program normally and with `LD_PRELOAD` pointing to the shared object.
Both runs must report `ret=-1 errno=9 size=4096` on this ABI.
The program uses descriptor -1 and does not open a GPU device.

## Bounded KWin diagnostic

Run as the same unprivileged user that runs the graphics session:

```sh
/bin/sh run-kwin-bo-trace.sh /absolute/v3d-bo-trace.so /absolute/new-trace-1280 1280x1024
/bin/sh run-kwin-bo-trace.sh /absolute/v3d-bo-trace.so /absolute/new-trace-640 640x480
```

The launcher creates separate HOME, XDG directories, and a D-Bus session.
It supplies LD_PRELOAD to the KWin command and removes it before the child D-Bus query.
It captures stderr in a private regular file and stops the session within 30 seconds.
The child saves `org.kde.KWin.supportInformation` if initialization reaches that point.
Inspect `status`, `client.status`, `compositor.stderr`, and `supportinformation.txt` when present.
Compare requested buffer sizes, allocation results, and closes across both dimensions.
A successful small run alone does not distinguish a size limit from memory fragmentation.
Keep the kernel revision and memory conditions with the runtime evidence.
