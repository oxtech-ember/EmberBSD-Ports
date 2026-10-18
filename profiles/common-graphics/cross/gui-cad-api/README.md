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
Install the normal runtime package closure separately. Verify the archive
SHA256 before extraction. Run `sh BUNDLE/run.sh BUNDLE NEW_LOG_DIRECTORY`.
The explicit `--without-glew` selection qualifies only the other three
consumers. It must not be described as GLEW acceptance.

NetBSD/AArch64 Valgrind support is unavailable in this workflow. The
target UBSan trap checks do not establish a Valgrind result. Display-backed
GLX, Wayland sessions and physical GPU drivers require separate tests.
