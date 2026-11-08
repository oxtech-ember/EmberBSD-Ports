# Mesa 26.2.4 patch inventory

The selected common source is [Mesa 26.2.4](https://docs.mesa3d.org/relnotes/26.2.4.html).
The four local patches are AI-assisted, not submitted upstream. Mesa source
licenses remain unchanged; new utility code is MIT and probe tests are
BSD-2-Clause. The archive URL and SHA256 are in [sources.tsv](sources.tsv).

## Current adaptations

- `patch-dso-lifetime` binds callbacks to the owning ELF DSO on NetBSD.
  Plain NetBSD `atexit` records no DSO owner. The helper uses `__cxa_atexit`
  with a typed trampoline and hidden local handle; it propagates allocation
  and registration failure and frees failed registrations. Other systems
  retain plain `atexit`. The implementation preserves reverse registration
  order across C++ destructors and C callbacks. It replaces the old
  unconditional `HAVE_NOATEXIT` destructor strategy.
- `patch-src_util_half__float.c` normalizes binary16 subnormals using integers,
  avoiding a binary32 subnormal intermediate flushed by the caller FP state.
- `patch-include_c99__alloca.h` selects compiler stack allocation on NetBSD
  in strict C11/C++17 modes. The libc declaration otherwise becomes an
  unresolved external call. No allocation shim or GNU dialect is introduced.
- `patch-bin_symbols-check.py` extends the existing upstream ELF bookkeeping
  allowlist to NetBSD without relaxing extra/missing API checks. Meson passes
  its target system explicitly, so a macOS host checks NetBSD ELF correctly.
  Direct native invocation retains the host default. The cross regression
  uses actual AArch64 ELF and native Mach-O libraries, including extra and
  missing export failures.

The lifetime patch covers all 13 registration sites in the selected source:
EGL, GLX, context, formats, extensions, options cache, locale, process name,
util queues, trace output, driver trace, optional Perfetto and ORC JIT.
Perfetto is disabled in this recipe but its cleanup remains adapted. All
remaining plain callbacks are in unselected physical Vulkan drivers or tools;
`tools=`, `vulkan-drivers=` and `vulkan-layers=` keep them outside this profile.
Native complete EGL/GLX/GBM/llvmpipe lifecycle checks still gate promotion.
The queue fixture tests callback dependencies; it does not replace the actual
Mesa queue or EGL integration tests. Its executable links pthread at startup:
NetBSD cannot initialize threading by loading libpthread late through a plugin.
Check this same constraint in dynamically loaded real graphics consumers.

The symbol policy also has a macOS cross check using the prepared compiler
and an existing Python interpreter. It builds small real target ELF and
native Mach-O libraries, then verifies target selection and export failures:

```sh
PYTHON=/absolute/python3.14 sh tests/mesa-symbols-cross.sh \
    PATCHED_MESA CROSS_GCC16_PREFIX TARGET_SYSROOT NEW_WORK
```

`tests/mesa-alloca.sh` takes the same four path arguments. It reconstructs
the unpatched header and requires both strict-mode links to fail, then
builds the patched C11/C++17 fixtures without an external `alloca` reference.
Run both outputs on the target with zero and several arguments to check
dynamic length, alignment, guard bytes and storage across another stack call.

## Disposition of all 44 previous patches

The former Mesa 21.3.9 set came from
[pkgsrc 0491f5e57e8fba00998bf1a6c0958ef421fefaa1](https://github.com/NetBSD/pkgsrc/tree/0491f5e57e8fba00998bf1a6c0958ef421fefaa1/graphics/MesaLib/patches),
plus three local fixes. Removing a patch is not a claim of upstream acceptance.
Identifiers below preserve the imported revision and authorship. Git retains
the original imported bytes and the superseded probe for comparison.

| Previous patch | Provenance | Disposition |
|---|---|---|
| patch-bin_symbols-check.py | Origin: EmberBSD; AI-assisted adaptation of the Mesa 21.3.9 test. | Rebased: existing ELF allowlist also applies on NetBSD; extra/missing public APIs still fail. |
| patch-src_compiler_builtin__type__macros.h | patch-src_compiler_builtin__type__macros.h,v 1.2 2019/08/31 17:56:09 nia Exp | Dropped: NetBSD 8 integer-name macro workaround; target NetBSD 11 headers use typedefs. |
| patch-src_drm-shim_drm__shim.c | patch-src_drm-shim_drm__shim.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: drm-shim tools explicitly disabled. |
| patch-src_egl_drivers_dri2_platform__drm.c | patch-src_egl_drivers_dri2_platform__drm.c,v 1.5 2020/01/21 14:41:26 nia Exp | Dropped: current GBM implements and exports gbm_format_get_name. Staging audit rejects mixed older GBM. |
| patch-src_egl_drivers_dri2_platform__x11.c | patch-src_egl_drivers_dri2_platform__x11.c,v 1.4 2022/03/13 15:50:05 tnn Exp | Dropped: old Darwin strndup is out of scope; current X11 screen selection supersedes DRI3 opt-in. Test software fallback and DRI3 separately. |
| patch-src_egl_main_eglglobals.c | patch-src_egl_main_eglglobals.c,v 1.2 2019/08/21 13:35:28 nia Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_gallium_auxiliary_pipe-loader_pipe__loader__drm.c | patch-src_gallium_auxiliary_pipe-loader_pipe__loader__drm.c,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: do not restore primary-node rendering to work around discovery. Use paired native render-identity libdrm/kernel adaptation. |
| patch-src_gallium_auxiliary_rbug_rbug__texture.c | patch-src_gallium_auxiliary_rbug_rbug__texture.c,v 1.1 2019/10/29 20:20:04 nia Exp | Dropped: old rbug directory and translation unit no longer exist. |
| patch-src_gallium_drivers_freedreno_freedreno__screen.c | patch-src_gallium_drivers_freedreno_freedreno__screen.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: Freedreno unselected; never substitute fabricated fixed RAM size. |
| patch-src_gallium_drivers_freedreno_freedreno__util.h | patch-src_gallium_drivers_freedreno_freedreno__util.h,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: Freedreno unselected. |
| patch-src_gallium_drivers_llvmpipe_lp__memory.c | patch-src_gallium_drivers_llvmpipe_lp__memory.c,v 1.1 2020/03/08 10:35:03 tnn Exp | Dropped: Apple-only data/BSS workaround; target is NetBSD/AArch64. |
| patch-src_gallium_drivers_nouveau_nouveau__vp3__video.c | patch-src_gallium_drivers_nouveau_nouveau__vp3__video.c,v 1.2 2019/08/21 13:35:28 nia Exp | Dropped: Nouveau unselected; target has O_CLOEXEC. |
| patch-src_gallium_drivers_nouveau_nv50_nv84__video.c | patch-src_gallium_drivers_nouveau_nv50_nv84__video.c,v 1.2 2019/08/21 13:35:28 nia Exp | Dropped: Nouveau unselected; target has O_CLOEXEC. |
| patch-src_gallium_drivers_vc4_vc4__bufmgr.c | patch-src_gallium_drivers_vc4_vc4__bufmgr.c,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: VC4 unselected. |
| patch-src_gallium_frontends_clover_util_range.hpp | patch-src_gallium_frontends_clover_util_range.hpp,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: obsolete Clover frontend/compiler workaround; Rusticl disabled. |
| patch-src_gallium_frontends_osmesa_osmesa.c | patch-src_gallium_frontends_osmesa_osmesa.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: old frontend removed upstream; no OSMesa library selected. |
| patch-src_glx_dri__common.c | patch-src_glx_dri__common.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_glx_dri__common.h | patch-src_glx_dri__common.h,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: Apple GLX-only declaration workaround. |
| patch-src_glx_glx__pbuffer.c | patch-src_glx_glx__pbuffer.c,v 1.1 2023/07/14 06:27:52 pho Exp | Dropped: old VMware pointer-screen layout no longer matches current embedded screen API; vmwgfx unselected. GLX runtime remains required. |
| patch-src_glx_glxclient.h | patch-src_glx_glxclient.h,v 1.3 2022/03/13 15:50:05 tnn Exp | Dropped: NetBSD uses ordinary thread_local in current u_thread.h, not initial-exec. |
| patch-src_glx_glxcurrent.c | patch-src_glx_glxcurrent.c,v 1.7 2025/03/07 07:00:33 wiz Exp | Dropped: same TLS model change; native platform probe also reads initialized TLS on existing/new threads. |
| patch-src_glx_glxext.c | patch-src_glx_glxext.c,v 1.2 2022/03/13 15:50:05 tnn Exp | Dropped: old DRI3 display initialization removed. Do not suppress DRI3 globally; native X11 software fallback/GLX gate promotion. |
| patch-src_glx_tests_dispatch-index-check | Origin: EmberBSD; AI-assisted adaptation of the Mesa 21.3.9 test. | Dropped: sed-based test removed upstream. |
| patch-src_intel_compiler_brw__fs__bank__conflicts.cpp | patch-src_intel_compiler_brw__fs__bank__conflicts.cpp,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: Intel compiler/driver unselected. |
| patch-src_intel_tools_aubinator__error__decode.c | patch-src_intel_tools_aubinator__error__decode.c,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: FreeBSD-only declaration in an unselected Intel tool. |
| patch-src_mapi_entry__x86-64__tls.h | patch-src_mapi_entry__x86-64__tls.h,v 1.6 2022/03/13 15:50:05 tnn Exp | Dropped: old dispatch removed; target AArch64, NetBSD no longer selects initial-exec. |
| patch-src_mapi_entry__x86__tls.h | patch-src_mapi_entry__x86__tls.h,v 1.7 2022/03/13 15:50:05 tnn Exp | Dropped: old dispatch removed; target AArch64, NetBSD no longer selects initial-exec. |
| patch-src_mapi_u__current.c | patch-src_mapi_u__current.c,v 1.4 2022/03/13 15:50:05 tnn Exp | Dropped: old unit removed. Current mesa/glapi/shared-glapi uses portable TLS. |
| patch-src_mesa_main_context.c | patch-src_mesa_main_context.c,v 1.6 2022/03/13 15:52:50 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_mesa_main_extensions.c | patch-src_mesa_main_extensions.c,v 1.3 2022/03/13 15:50:05 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_mesa_main_formats.c | patch-src_mesa_main_formats.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_mesa_main_shader__query.cpp | patch-src_mesa_main_shader__query.cpp,v 1.2 2019/08/21 13:35:28 nia Exp | Dropped: Apple GLhandleARB pointer conversion only. |
| patch-src_mesa_x86_common__x86.c | patch-src_mesa_x86_common__x86.c,v 1.3 2019/08/21 13:35:28 nia Exp | Dropped: DragonFly x86 SSE detection only. |
| patch-src_util_build__id.c | patch-src_util_build__id.c,v 1.1 2019/08/21 13:35:28 nia Exp | Dropped: FreeBSD/DragonFly ElfW expansion only; NetBSD unchanged by old patch. |
| patch-src_util_disk__cache__os.c | patch-src_util_disk__cache__os.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: target dirent has d_type and DT_REG; do not weaken file-type checks. |
| patch-src_util_half__float.c | Origin: EmberBSD; AI-assisted Mesa 21.3.9 adaptation. | Retained: integer normalization fixes reproduced subnormal-flush failure; exhaustive actual-source regression. |
| patch-src_util_libsync.h | patch-src_util_libsync.h,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: SunOS ioccom include only; NetBSD already includes ioctl definitions. |
| patch-src_util_strndup.h | patch-src_util_strndup.h,v 1.2 2019/08/21 13:35:28 nia Exp | Dropped: pre-10.7 Darwin compatibility only. |
| patch-src_util_u__atomic.h | patch-src_util_u__atomic.h,v 1.2 2019/08/21 13:35:28 nia Exp | Dropped: SunOS compiler workaround only. |
| patch-src_util_u__printf.h | patch-src_util_u__printf.h,v 1.1 2022/03/13 15:52:50 tnn Exp | Dropped: current upstream header includes stdarg.h. |
| patch-src_util_u__process.c | patch-src_util_u__process.c,v 1.1 2022/03/13 15:52:50 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_util_u__qsort.h | patch-src_util_u__qsort.h,v 1.1 2025/03/07 06:56:20 wiz Exp | Dropped: Meson detects GNU/BSD qsort_r signatures. |
| patch-src_util_u__queue.c | patch-src_util_u__queue.c,v 1.3 2022/03/13 15:50:05 tnn Exp | Replaced by owner-scoped util_atexit: retain registration order and run only registered cleanup before DSO unload. |
| patch-src_util_u__thread.h | patch-src_util_u__thread.h,v 1.5 2022/03/13 15:50:05 tnn Exp | Dropped: NetBSD naming upstream in u_thread.c; Meson excludes incompatible affinity and uses ordinary TLS. |

## Version and ABI boundaries

GCC 16.2.0 and common LLVM 23.1.2, Meson 1.12.1 and Python 3.14.8 are
required without older-library fallback. We select ORC JIT for the current
LLVM path; upstream AArch64 can still choose MCJIT. ORC JIT, llvmpipe, softpipe
and classic VirGL remain enabled together. Vulkan, video frontends, Rusticl,
physical-driver tools and GLVND are outside this initial probe.
Mesa 26 installs `libgallium-26.2.4.so`; shared libglapi is no longer installed.
Retain the current SONAME. Audit and rebuild Qt/GNOME/Xorg
consumers against the common ABI before package promotion. The
[temporary headless cross diagnostic](../../profiles/common-graphics/cross/README.md)
has separate softpipe board evidence; it does not establish the complete
shared-LLVM23 package or X11/Wayland renderer acceptance.

The 2026-10-06 native ABI inventory found Qt6Gui 6.11.1 depends on base
libEGL.so.0/libGL.so.3/libstdc++.so.9, while Mutter 40.2 and COGL depend on
libEGL.so.0. Base EGL/GL/GBM require libglapi.so.1 and libdrm.so.3. The selected
non-GLVND Mesa source instead declares libEGL.so.1/libGL.so.1 and libgallium;
these are concrete consumer rebuild requirements. Startup pthread linkage
is also required for clients that load worker-using libraries dynamically.
