# Common spatial and geometry providers

`math/rectpack2d`, `math/rtree`, and `math/tinyspline` provide shared rectangle
packing, spatial indexing, and spline APIs. Consumers use their installed
headers and exported CMake targets instead of private copies.

The cross-link consumer in
[`tests/spatial-geometry-providers`](../tests/spatial-geometry-providers/CMakeLists.txt)
resolves the exported targets and links representative API calls, including
the TinySpline C++ `BSpline::sample()` vector-returning API, against the
selected AArch64 sysroot. The retained `tinyspline` package currently fails
that C++ link because its C++ wrapper imports
`ts_chord_lengths_length_to_knot` but its C library does not export the
function. The common recipe now marks that declaration as public and bumps the
package revision; the cross-link must be repeated against the rebuilt package
before the C++ provider is accepted. This check does not execute target code.
The package also carries its focused C API workspace regression under
`pkgsrc/math/tinyspline/tests/`.
