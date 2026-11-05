# Shared Ports library consumer

This focused CMake consumer imports the installed package interfaces used by
KiCad 10.0.8, compiles against their actual headers, and links the shared
libraries. It covers argparse, dynamic_bitset, Clipper2's Z-enabled API,
FastFloat, fmt, nlohmann/json, NanoSVG, nanodbc, tl::expected, and pybind11's embedding interface. Required package
discovery fails without a provider; the KiCad patch does not fall back to
source copies.

Configure it with CMake from the selected SDK and the same compiler bindings,
target, sysroot and runtime flags as the Ports build. Pass the installed target
prefix through `CMAKE_PREFIX_PATH`; a toolchain file, if used, is an explicit
input from that build, not a fixed SDK filename. Reuse its build directory on
subsequent runs. Resolve parallelism with SDK `scripts/resolve-jobs.py`.

The adjacent `../pegtl` consumer takes `KICAD_SOURCE_DIR` pointing to the patched
KiCad sources. It exercises real library-table and CADSTAR grammars, parse-tree
ownership, source labels, and LF/CRLF error positions with the shared PEGTL.
Run its CTest target on the build host for a native build or on EmberBSD for a
cross build. KiCad's own `test_pegtl` diagnostic tool remains available with the
Ports `tests` option.

These focused checks do not replace the full KiCad package build or target
application acceptance.
