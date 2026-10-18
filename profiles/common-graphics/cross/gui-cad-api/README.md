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

The producer checks all four package payloads against their installed
catalogs and archives. It records source commits, compiler identities,
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
