# KiCad in Ports

`cad/kicad10` selects KiCad 10.0.8, released on
[2026-10-30](https://www.kicad.org/blog/2026/10/KiCad-10.0.8-Release/),
with matching symbols, footprints, templates and 3D models. The normal SDK
package client resolves this root, reuses compatible binary packages and builds
missing dependencies through the common Ports graph:

```sh
python3 scripts/packages.py --config /path/to/sdk-client.json \
    install --package cad/kicad10
```

The shared version-family rule removes the older upstream `cad/kicad` recipe
from exports and rejects it as a build root. The resource packages keep their
unversioned paths; there is one current application recipe, `cad/kicad10`.

Run that command from the SDK checkout with the selected SDK host Python.
The SDK configuration selects the host tools, target, compiler and sysroot;
the KiCad recipe does not choose a board or require a target build machine.

## Shared dependencies

The recipe uses the common providers for geometry, parsing, rendering, database
access, Python embedding and IPC. It does not fall back to bundled copies when
a provider is missing. Buildlinks declare the dependencies; CMake consumes their
installed interfaces.

Where KiCad maintains changes needed by its consumers, the common provider
retains them: the NanoSVG FILE interface, CompoundFileReader validation and
UTF-16 support, bounded gzip decompression, RTree traversal, TinySpline workspace
handling, and DXF parser/writer repairs. Their recipes retain source provenance
and licenses. Source archives are fetched once through the shared distfiles
cache; Ports stores recipes and patches rather than copied library sources.

GLAD is generated from its upstream packaged Khronos specifications. The
3DxWare provider preserves KiCad's GPL navigation API subset; its loader still
returns unsupported on BSD. It does not provide a 3Dconnexion hardware driver.
Only KiCad's Lemon build adapter and wxWidgets Markdown adapter remain under
`thirdparty/`; they use the shared Lemon and Sundown providers.

PEGTL 4 uses explicit owning/view inputs and typed error positions. The KiCad
adaptation preserves parser diagnostics and parse-tree ownership. Header-only
dependencies are build dependencies; compiled libraries remain ordinary runtime
packages. Lemon runs on the host. Python generators use the host interpreter,
while embedding and the `pcbnew` extension use target headers and libraries.

The existing pkgsrc choice `KICAD_SCRIPTING_WXPYTHON=OFF` is retained. Core Python
embedding, the SWIG module, IPC, WebView, translations and the selected SPICE
support remain enabled. QA binaries and the shared Turtle mock library are
selected with `PKG_OPTIONS.kicad+=tests` and are separate from the normal
application build.

The focused consumers in [tests](tests/shared-libraries/README.md) exercise shared
interfaces and parser behavior. They do not replace building the complete
package or running CAD workflows on EmberBSD.

Full application configuration, linking and CAD runtime acceptance remain
pending the common GTK4 wxWidgets/WebKit stack. The recipe and focused consumer
checks are not evidence of a completed KiCad binary package.
