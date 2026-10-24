# GBM GCC16 checks

The AI-assisted patch uses the GCC/Clang ELF `weak` attribute for the optional
`gbm_bo_get_fd_for_plane` declaration. GCC rejects the previous `weak_import`
attribute. The function signature, presence check, fd error check and complete
DRM fallback remain unchanged. The BufferUsage switch gains one fatal terminal
after its existing cases. No mapping or runtime feature changes.

GCC documents [ELF weak symbols](https://gcc.gnu.org/onlinedocs/gcc/Common-Attributes.html#weak).
The same Chromium file previously used
[weak declarations for optional GBM functions](https://chromium.googlesource.com/chromium/src/+/e598eece8a61d84b31794fe964aac39cca0b6d76/ui/gfx/linux/gbm_wrapper.cc).
The inspected NetBSD and FreeBSD patches do not repair this attribute.
This file belongs to Linux/BSD ELF targets; the change does not select Darwin
host-object attributes.

Replay the complete production GCC16 commands for `gbm_wrapper.cc` and
`gbm_util.cc`. Both original commands fail; both patched commands compile.
Read the patched wrapper object with target `readelf -Ws`. Its optional symbol
must have `WEAK DEFAULT UND` binding. Both Clang Static Analyzer pairs complete
with unchanged signatures: one inherited unused plane-count initialization in
the wrapper, and none in the utility. All four Cppcheck inputs stop at unchanged
dependency parser errors.

The [small binding fixture](gbm-weak/main.cc) includes the actual production
declaration. Extract its entire `extern "C"` block from `gbm_wrapper.cc` to an
owned `gbm-weak-declaration.h`. Do not replace its attribute independently.
Compile the fixture with the production target flags and that include directory.
The original declaration fails on GCC16; the patched declaration compiles.
Link with the common target runtime. Build [provider.cc](gbm-weak/provider.cc) as
an owned shared object. Its synthetic function tests symbol binding only.
It does not implement or test GBM buffer operations.

On the target, run the executable without a provider: expect status zero.
With an extra argument and no provider, expect status 2. Select the provider
through an absolute `LD_PRELOAD` path and pass an extra argument: expect zero.
With the provider and no extra argument, expect status 1. All four cases passed
on physical NetBSD 11 AMD64 with the common GCC16 runtime. The target loader
resolved the optional symbol to null or the test provider as intended.
Paired fixture Cppcheck and Clang Static Analyzer checks complete without
findings. These checks do not execute DRM, a real GBM call, GPU rendering,
Electron or Blanc.
