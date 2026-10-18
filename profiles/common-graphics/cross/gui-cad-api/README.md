# Installed GUI/CAD API checks

These consumers exercise the normal installed GLU 9.0.3, Cairo 1.18.6,
GLM 1.0.3nb1 and GLEW 2.3.1 providers. They do not establish a display
session, hardware rendering or a complete CAD application.

`glu-api` tessellates a concave L polygon into four triangles with total
area 5. It checks known projection values, the inverse and a singular
inverse refusal. `cairo-api` checks exact image pixels, PNG round trips,
PDF/SVG output and real stream failures across four lifecycles.
`glm-api` uses the installed CMake target for an affine transform,
inverse, determinant and quaternion with known numerical values.
`glew-egl` requires successful extension dispatch and exact pixels in
four real desktop OpenGL contexts created through surfaceless EGL.
It also requires rejection before context creation and after release.

Use the selected CPython 3.15 host interpreter. Pass a clean SDK source
with host API 1. Pass clean Ports sources, the common GCC16 cross tools,
an installed SDK and the matching normal package archive directory:

```sh
python3.15 prepare.py --sdk-source /path/to/EmberBSD-SDK \
  --sysroot /path/to/sysroot --cross-tools /path/to/cross-tools \
  --cmake /path/to/host/cmake --packages /path/to/packages/All \
  --work /path/to/new-work
```

The producer checks all four packages' file bytes, file modes and links
against their installed catalogs and archives. It records source commits, compiler identities,
commands, ELF metadata and hashes. It compiles every target executable
with GCC16 and UBSan traps. The bundle contains no replacement libraries.
The target runner checks the bundle and installed runtime hashes, then
rejects loaded libraries outside the recorded canonical provider set.
It requires one compiler-support provider per process. GLU, GLM and Mesa
use common GCC16. The C-only Cairo consumer follows the fork libm's
`/lib` RPATH and uses its original base compiler-support library. Both
files come from the same SDK. Their hashes and required consumers are
explicit. The runner rejects provider coexistence and base C++ runtimes.
Install the normal runtime package closure separately. Verify the archive
SHA256 before extraction. Run `sh BUNDLE/run.sh BUNDLE NEW_LOG_DIRECTORY`.
The default selection qualifies GLU, Cairo and GLM. The optional
`--with-glew-egl` selection also requires GLEW EGL acceptance. GLEW's
default Unix build calls `glxewInit()` after initializing OpenGL. A valid
EGL context without a GLX display can therefore fail with code 4.
Keep that failure visible. KiCad 10.0.7 uses GLAD in
`common/gal/opengl/opengl_gal.cpp`; it does not use this GLEW initialization.

NetBSD/AArch64 Valgrind support is unavailable in this workflow. The
target UBSan trap checks do not establish a Valgrind result. Display-backed
GLX, Wayland sessions and physical GPU drivers require separate tests.
UBSan instruments these consumers. It does not instrument the installed
libraries or establish a clean memory result for their complete code.

## Accepted AArch64 scope

On 2026-10-18, the default GLU, Cairo and GLM contracts passed in the
EmberBSD AArch64 VM. Each process passed installed-library SHA256 checks,
its live canonical provider inventory and its required compiler-support
selection. The normal dependency transaction passed `pkg_admin check`
for 11,896 files in 67 packages. This is library acceptance without a
display session or complete CAD application.

The accepted consumer source is Ports commit
`af46f9930b54e237dab9e641199200d00e0fa0db`.
The host uses GCC 16.2.0, CPython 3.15.0 and SDK host API 1 from SDK commit
`9b228882bea2e087e229c995d022e59d7cd29880`.
The consumer archive SHA256 is
`556a1a2a26b0750ee78cd3d45c53444f0fe5518b7719ab0d557407010089bbbe`.
Its Mesa provider is 26.2.4nb9 with LLVM 23.1.3.

| Normal package | Archive SHA256 |
| --- | --- |
| glu-9.0.3 | `779092724cfe5f19a66e0034bbf696653a7fe25040d5656d486e167da1f5cba6` |
| cairo-1.18.6 | `bc11086a8389f50e2d0f11521c005d47534935127252976e0fa2d6072c22feef` |
| glm-1.0.3nb1 | `12b47b2e26a0ea3875ad7be53e8ac3737f9a5e1d1ee137a1aa8b8d97ce69779a` |
| glew-2.3.1 | `3dd67e0aa4a53cca5718f4588130d9c0b70e26129c4981ef09d85b81e835df9a` |

The optional GLEW EGL diagnostic fails with `GLEW_ERROR_NO_GLX_DISPLAY`
after creating a real Mesa OpenGL 4.6 compatibility context. The renderer
is llvmpipe. This result does not qualify GLEW EGL or display-backed GLX.
KiCad's GLAD loader remains a separate application check.

Twelve host refusal cases retain failed outputs without an accepted
archive. They cover input reuse/overlap, wrong compiler/API, dirty SDK,
missing packages, independent file/mode/link/catalog/archive drift and
an actual GCC16 link forced to the base C++ runtime. The last case verifies
that the producer rejects `libstdc++.so.9` before archive creation.

GCC16 `-fanalyzer` covers the three C units. Clang 19.1.7 analyzes all
four units with the actual target headers; it builds no target objects.
Both report no diagnostics. Cppcheck 2.22.0 reports only style findings
for the GCC-preprocessed GLU/Cairo units. Its GLEW pass stops at the
upstream header's line 3685. Its complete GLM pass stops in the fork's
`sys/endian.h`. The additional modeled-header GLM pass retains upstream
template, copy and portability findings. These parser limits and findings
remain visible; this is not a clean whole-library Cppcheck result.
