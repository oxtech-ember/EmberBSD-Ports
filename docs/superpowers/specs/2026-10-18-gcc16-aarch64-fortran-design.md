# GCC16 AArch64 Fortran Cross-Support

## Goal

Enable current GCC 16.2 Fortran packages to cross-build for EmberBSD AArch64. Use this support to build the current NumPy 2.5.3 package with BLAS and then build openTPU.

## Design

- Use the existing `aarch64--netbsd` GCC16 toolchain and EmberBSD sysroot.
- Add the GCC Fortran frontend and the target Fortran runtime required by real ELF dependencies.
- Package target runtime libraries through the existing `gcc16-runtime` provider. Keep one GCC16 ABI and prefix.
- Add pkgsrc cross compiler and Libtool support through the Ports export patches. Do not modify the pinned pkgsrc submodule directly.
- Keep ordinary NumPy BLAS integration. Do not add a no-BLAS package variant or an older compiler or library.
- Verify compiler identity, target ELF, runtime dependencies, and absence of host paths. Build NumPy and openTPU with pkgsrc checks enabled.

## Acceptance limits

This work accepts cross-compilation and package creation only. It does not claim execution on EmberBSD, RTL acceptance, inference, or FPGA support. The existing local openTPU CPU tests remain host-side evidence.
