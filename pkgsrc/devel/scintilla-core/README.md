# Scintilla core provider

This recipe prepares the toolkit-free Scintilla 5.6.9 editing core as
`libscintilla-core.a`, compiled with C++17 and position-independent code. It
contains the upstream `gtk/makefile` `SRC_OBJS` plus `ScintillaBase`, exactly the
`.cxx` files in `src/`. It does not build `PlatGTK`, `ScintillaGTK`, accessibility,
or a widget marshaller, and has no GTK dependency.

The frontend supplies the real `Platform.h` and `Debugging.h` implementations,
including surfaces, fonts, windows, list boxes and menus. Linking the archive
into the frontend's DSO resolves this boundary normally; a standalone core DSO
would instead require unresolved backend symbols and loader-specific policy.
No backend stubs or dynamic-lookup linker exception are provided.

`SCINTILLA_CORE` is private to the archive build and leaves all upstream `PLAT_*`
selectors zero. The installed header still selects `__WX__`, GTK, etc. for real
frontend code. In 5.6.9 the generic sources use only `PLAT_GTK_MACOSX` for GTK/macOS
key mapping and `PLAT_CURSES` for calltip drawing; neither changes class layout.
This core retains the normal graphical keymap/calltip path used by wx. The
upstream `__APPLE__` calltip-border distinction follows the selected target OS.
A future curses or GTK/macOS consumer must account for those behavior choices;
this package does not silently claim identical behavior for every frontend.

## Consumer contract

Public interfaces are installed under `include/scintilla-core`; private editing
headers are under `include/scintilla-core/private`. Neither directory collides
with the old `devel/scintilla` package. The GTK widget header and the separate
ScintillaCall wrapper header are not advertised by this core-only package.

```cmake
find_package(ScintillaCore 5.6.9 EXACT CONFIG REQUIRED)
target_link_libraries(frontend PRIVATE Scintilla::Core)
```

`Scintilla::Core` exports both header directories, C++17 and the thread dependency.
`Scintilla::Headers` exports only the public interfaces. The equivalent
pkg-config modules are `scintilla-core` and `scintilla-headers`; an Autoconf
frontend using private classes must request `scintilla-core = 5.6.9` and select
C++17 or newer. Private headers and core objects must come from the same source
version and compatible compiler/runtime ABI. Rebuild frontend consumers after
an incompatible core change; this is not a stable private C++ ABI promise.

`Makefile.common` owns the version, archive, distinfo, patches and preparation
files for future frontend recipes. New consumers must reuse it, not download
another Scintilla source copy. `x11/wxGTK32` consumes this core and the shared
Lexilla provider; this core package does not supply a GTK widget frontend.

## Source and verification

The [official current release](https://www.scintilla.org/ScintillaDownload.html)
is 5.6.9. The [source archive](https://www.scintilla.org/scintilla569.tgz) has
SHA256 `1622546ce1d3804b589292f1adae98ad1d87fa8c43bb401edc098adae12dcacb`.
`License.txt` is the upstream HPND notice and is installed intact. The only source
patch introduces the explicit neutral platform selector; CMake packaging is
provided by the common recipe.

The `tests` package option is off by default. When selected, it builds a consumer
DSO against the PIC archive and an executable checking Unicode conversion,
supplementary characters, empty input and malformed UTF-8. `bmake test` runs it
only on a compatible runtime. The same `tests/` CMake project can consume an
installed package using its selected native or cross toolchain. Target programs
must run on the target or an explicitly configured emulator, not on the host.

Archive integrity, source-set comparison and patch preparation are checked.
The native source build with the selected Clang 23.1.4 passed. The opt-in
Unicode/PIC contract passed both in the build tree and through an installed
CMake consumer; the installed pkg-config consumer also compiled, linked and ran
with the staged library directory on the loader path. These are diagnostic
source-build checks. The normal SDK client also built and installed the aarch64
Ports package. Its standalone CMake consumer was cross-built against that
installed provider and passed in an EmberBSD/NetBSD 11 aarch64 guest, including
the real PIC DSO link and Unicode checks. The test used the selected sysroot
C++ runtime in a temporary guest directory; it did not install development
tools on the guest. The package retained its default tests-off setting.
These focused contracts do not establish full wx frontend/GUI acceptance.
