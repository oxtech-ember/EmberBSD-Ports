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
Embedding consumers use the shared `pybind11::embed` CMake target, including its
transitive headers and Python link requirements. KiCad does not extract a global
include path from the provider's internal target layout.
Cross builds retain the selected target Python headers and libraries instead of
letting pybind11 replace them with the native generator interpreter's paths.

The existing pkgsrc choice `KICAD_SCRIPTING_WXPYTHON=OFF` is retained. Core Python
embedding, the SWIG module, IPC, WebView, translations and the selected SPICE
support remain enabled. QA binaries and the shared Turtle mock library are
selected with `PKG_OPTIONS.kicad+=tests` and are separate from the normal
application build.

The focused consumers in [tests](tests/shared-libraries/README.md) exercise shared
interfaces and parser behavior. They do not replace building the complete
package or running CAD workflows on EmberBSD.

The full aarch64 package builds and links with the common GTK4 wxWidgets/WebKit
stack. Host Python runs the build generators. The installed application uses
the Python interpreter supplied by its target package dependency.
On EmberBSD aarch64, the ECC83 demo's XML netlist matches upstream KiCad
10.0.8 for all 15 components and all 33 pins across 13 nets. The schematic
and the board's front copper layer also export to SVG. Eeschema opens and draws the
packaged schematic under Xvfb with software rendering after the first-run
wizard initializes the default libraries. Physical GPU testing remains open.

The runtime includes the common DejaVu TrueType fonts so that a minimal target
can render text, including Cyrillic. Type 1 fonts alone do not satisfy current
Pango's font loader.

Unix toolkit discovery selects the shared GTK4 provider. An explicit toolkit
selection is retained. wxPython toolkit checks run only when wxPython is enabled.
The causal check runs the actual CMake selection block, KiCad's find module and
the installed target configuration script:

```sh
python3 tests/wx-toolkit.py --source /prepared/kicad \
  --wx-config /sysroot/usr/pkg/lib/wx/config/aarch64--netbsd-gtk4-unicode-3.2 \
  --prefix /sysroot/usr/pkg --cmake /native/bin/cmake --work /work/wx-toolkit
```

Use the selected SDK build PATH, including its host `sh` route. The check covers
Unix default and explicit GTK4 selection, Apple provider selection, and matching
or conflicting wxPython toolkits. It does not execute target programs.

The platform and native-print QA targets share one GTK4 pkg-config target.
The Unix platform adapter uses the common wx native theme and GtkComboBoxText
model, GdkSurface coordinates and the existing Wayland pointer-constraints
protocol. It does not query removed GTK3 settings or use the old GtkMenu/ATK
choice workaround. WebKit6 cookie deletion submits an asynchronous request via
the view's NetworkSession; submission does not establish completion. Remote
file dialogs still need a local filename, such as a mounted remote filesystem.

Both platform translation units pass target syntax checks with Wayland enabled.
WebView's Clang Static Analyzer check is clean; UI retains an unchanged wx trace
formatting finding outside the adapter changes. The known Cppcheck target-header
parser limitation remains. `tests/ui4-contract.py` extracts the actual theme,
choice, scale and icon methods into a focused runtime fixture:

```sh
python3 tests/ui4-contract.py \
  --source /prepared/kicad/libs/kiplatform/port/wxgtk/ui.cpp \
  --output /work/ui4-contract.cpp
```

Build it with the selected target wx/GTK4 and KiCad platform headers; run it on
the target with a display and `GDK_SCALE=2`. Full GUI acceptance, Wayland pointer
constraints and asynchronous WebKit cookie completion remain pending.

The GL context manager uses the public wx canvas visibility precondition on
GTK4. Its EGL pbuffer does not require the removed GTK3 drawing-window accessor.
`tests/gl-context4.cpp`, linked with the actual
`common/kicad_gl/gl_context_mgr.cpp`, the prepared KiCad headers and installed
target wx GL/core/base and EGL libraries, checks hidden/shown canvases, repeated
lock/unlock, an alternate canvas and a hidden parent. Run it on a target display
with a bounded timeout and fatal GTK criticals. This focused lifecycle check
reuses the wx GL backend acceptance; it does not establish full CAD rendering
or physical GPU support.

## Ordered vector coordinates

KiCad's `VECTOR2I::operator<` compares vector lengths for geometric operations.
Different points at the same distance from the origin compare equivalent under
that ordering. Maps and sets that identify points by position use the explicit
`VECTOR2I_MAP` and `VECTOR2I_SET` aliases, which compare x then y. The
`tests/vector-order.cpp` target fixture checks map insertion, lookup and mapped
values, plus set insertion for `(3, 4)` and `(4, 3)`.

Compile the fixture and `libs/kimath/src/math/vector2.cpp` with the target C++
compiler, the kimath include directory and the directory containing the generated
`config.h`. Run the resulting executable on the target.

The bundled ECC83 schematic exercises this distinction in the actual editor.
Export it from a fresh profile and check which pins belong to ground and to
the heater connector. Run these commands as an ordinary user on EmberBSD from
the directory containing this recipe, or copy the test alongside the export.

```sh
work=$(mktemp -d)
export KICAD_CONFIG_HOME="$work/config"
demo=/usr/pkg/share/kicad/demos/ecc83/ecc83-pp.kicad_sch
kicad-cli sch export netlist --format kicadxml -o "$work/ecc83.xml" "$demo"
python3.15 tests/ecc83-connectivity.py "$work/ecc83.xml"
kicad-cli sch export svg -o "$work" "$demo"
```

For ERC on a headless system, initialize the profile with the default library
tables shipped in the package. These commands use the fresh profile above.

```sh
mkdir -p "$KICAD_CONFIG_HOME/10.0"
tables=/usr/pkg/share/kicad/template
cp "$tables/fp-lib-table" "$tables/sym-lib-table" "$KICAD_CONFIG_HOME/10.0/"
kicad-cli sch erc --format json --severity-all -o "$work/ecc83-erc.json" "$demo"
```

With these tables, ERC reports zero violations for ECC83. An empty profile
produces six warnings about the unconfigured capacitor and resistor footprint
libraries.
