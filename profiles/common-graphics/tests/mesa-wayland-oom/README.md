# Wayland back-buffer allocation contract

MesaLib 26.2.4nb7 clears the cached back-buffer alias when `get_back_bo` fails.
The color-buffer slot and any partial image remain owned by the surface.
A later callback retries allocation instead of exporting a null image.
Persistent allocation failures still return `EGL_BAD_ALLOC`.
This change does not increase GPU memory limits or hide allocation failures.

```sh
ruby run.rb /absolute/mesa-26.2.4.tar.xz /absolute/new-output
```

The runner verifies the pinned archive SHA512 and canonical pkgsrc patch SHA1.
It extracts six complete functions from the actual `platform_wayland.c`:
`wait_for_free_buffer`, `get_back_bo`, `update_buffers`, `update_buffers_if_needed`,
`image_get_buffers`, and `dri2_wl_swap_buffers_with_damage`.
It does not edit their bodies in the test.
The fixture doubles image allocation, DRI export, tracing, and Wayland calls.
A null image at the export boundary is counted without dereferencing it.
This makes the baseline failure deterministic without a deliberate host crash.

The baseline accepts a selected slot after its allocation failed.
The patched source retries, reports repeated allocation failure, and recovers when allocation succeeds.
Single-GPU and separate render/display-GPU paths run independently.
The test checks that no failed image reaches export, attach, or commit.
It also checks that partial resources remain owned and successful swaps still work.

Normal and strict ASan/UBSan runs are required. The runner emits a compilation database.
Use that database for Cppcheck and preserve baseline and patched analysis results.
The initial checks used Cppcheck 2.22, Clang Static Analyzer, and GCC 16.2 `-fanalyzer`.
The GCC check used the EmberBSD/AArch64 sysroot and compiled target objects.
Valgrind was unavailable on the macOS/arm64 host. Sanitizers are not Memcheck.

These checks validate source control flow. They do not allocate native GPU buffers.
Full Mesa packaging, native OOM behavior, Wayland presentation, and desktop stability remain separate checks.
