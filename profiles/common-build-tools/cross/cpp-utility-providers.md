# Common C++ utility providers

`math/nanoflann`, `security/picosha2`, `textproc/parson`, and
`textproc/rapidcsv` are common package providers. Consumers use their installed
headers and CMake targets where provided rather than carrying private copies.
The normal exporter adds these common `pkgsrc/` overlay recipes to the package
catalog. `pkgsrc/replaces` applies only when an overlay replaces an existing
upstream recipe.

The cross-link consumer in
[`tests/cpp-utility-providers`](../tests/cpp-utility-providers/CMakeLists.txt)
checks the CMake imports, header interfaces, and Parson's target link. It does
not execute the target program. Existing AArch64 package build/install results
remain the package evidence for this source revision.
