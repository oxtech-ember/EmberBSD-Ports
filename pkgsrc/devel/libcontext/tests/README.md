# Context ABI check

Configure this consumer with the selected SDK compiler and the installed
`libcontext` CMake package. A cross build uses the same target, sysroot and
runtime as the package build. Run the executable on that target, or CTest for
a native build. The two transfers check argument delivery and resumption of
a suspended stack through the shared library.

This is an explicit acceptance check; it does not run during package builds.
