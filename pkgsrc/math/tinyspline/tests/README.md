# TinySpline focused test

`interpolate_workspace.c` exercises the public natural cubic interpolation and
evaluation APIs for three points in dimensions 2, 3, and 4. The 3D and 4D
cases catch overlap between the first input point and the first Thomas-solver
result while the workspace is rearranged.

As an installed consumer, compile this file against the TinySpline and Parson
headers and libraries from the package installation. To run the focused test
under AddressSanitizer and UndefinedBehaviorSanitizer, compile the actual
`tinyspline.c` source with the common Parson `parson.c` source and their public
header directories. This sanitizer invocation uses the sources to instrument
the provider; it does not define a separate library or package owner.
