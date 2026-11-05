# PEGTL 4 compatibility check

This pilot uses the pinned VTK 9.5.2 MotionFX grammar header and the patched
`FindPEGTL.cmake`. It verifies that the imported include directory is the
include root required by VTK's `<tao/...>` headers, then builds and runs the
actual grammar with PEGTL 4.0.2.

Configure with the selected native CMake/compiler and the staged PEGTL prefix:

```sh
cmake -S tests/cmake -B /tmp/vtk-pegtl4-check \
  -DCMAKE_CXX_COMPILER=/selected/native/prefix/bin/clang++ \
  -DVTK_SOURCE=/path/to/VTK-9.5.2 \
  -DPEGTL_PREFIX=/path/to/pegtl-prefix
cmake --build /tmp/vtk-pegtl4-check
/tmp/vtk-pegtl4-check/vtk_pegtl4_compat
```
