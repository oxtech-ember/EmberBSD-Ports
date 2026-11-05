# NanoSVG KiCad API snapshot

This package exposes the NanoSVG API shipped in KiCad 10.0.8 as the shared
CMake target NanoSVG::nanosvg and installs include/nanosvg.h.

The source is the thirdparty/nanosvg subtree of the official
[KiCad 10.0.8 source](https://gitlab.com/kicad/code/kicad/-/tree/10.0.8/thirdparty/nanosvg),
dated 2026-10-29 in the source files. The package extracts only that subtree
from kicad-10.0.8.tar.bz2; it does not carry a second source copy. The archive
SHA-256 is
e349755a725b5dd2ae43c5bac20b2c5504fd4f788d3bc84e84712b01349e5828.

[KiCad's README.txt](https://gitlab.com/kicad/code/kicad/-/raw/10.0.8/thirdparty/nanosvg/README.txt)
identifies [memononen/nanosvg](https://github.com/memononen/nanosvg) as the
origin, preserves its Zlib license, and explains that the header-only
implementation was split into nanosvg.cpp. The supported API also accepts a
FILE * in nsvgParseFromFile() and provides nsvgDuplicatePath(). The original
NanoSVG [upstream README](https://github.com/memononen/nanosvg#readme)
describes the project as not actively maintained and documents the header-only
NANOSVG_IMPLEMENTATION model with filename-based file input. This package
therefore follows KiCad's maintained snapshot and API instead of replacing it
with an incompatible upstream header-only release.

The CMake patch adds a shared library, exported NanoSVG::nanosvg target and
package config. make test builds and runs the small FILE-based SVG consumer as
an explicit package test.
