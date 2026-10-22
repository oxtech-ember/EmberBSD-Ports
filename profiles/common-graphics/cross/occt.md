# Common OCCT 8.0.1 provider

The canonical `cad/occt` package uses official OCCT 8.0.1. Its API and ABI
buildlink floors are 8.0.1. KiCad uses this provider in the normal prefix.
The source archive, upstream revision, licenses and authoritative source
patches are recorded in [the source probe](../../../probes/kicad/occt/README.md).
The exporter checks the archive pin and every recipe patch before materializing
an isolated pkgsrc source view. It dereferences only the declared patch links.

The default package retains the seven standard modules, shared libraries,
Draw, Xlib/OpenGL, FreeType/fontconfig, FreeImage, Eigen and RapidJSON.
The Draw option uses the common Tcl/Tk 9.1 pair. FreeImage is independent
of Xlib selection. Release exception and range checks remain enabled.
The normal Bash provider supplies the target launcher. Native Bash remains
a separate build tool. Target scripts use `/usr/pkg/bin/bash`.

Cross builds use the common GCC16 profile. Native generators stay on the
build host. CMake 3.10 is the upstream compatibility floor. The qualified
build uses current CMake through the shared `EMBERBSD_BUILD_CMAKE` contract.
This compatibility floor does not require installation of an old CMake.

The complete GCC16 AArch64 package passes ordinary stage and package checks.
Its static inventory has 7,906 payload entries, including 68 shared libraries
and the Draw executable. All 69 ELF files are AArch64. The archive matches
every staged byte, mode and link. The installed package also matches all
7,906 payload entries and its package registration.

The recipe sets an explicit empty `3RDPARTY_DIR:PATH`. This prevents upstream
from using a source directory only during the first configure. The actual
source regression checks first and repeated configuration, script installation
and the single `DESTDIR` boundary. Two strict post-install substitutions remove
the producer buildlink prefix from the compiler-driver script and replace
the cross SDK prefix in exported linker flags with the imported package prefix.
All 21 installed shell and CMake files contain no producer paths. A relocation
check imports all 68 library targets and headers from two different prefixes.

The 292 Draw-only packing-list entries follow actual source ownership and the
complete stage. Draw resources remain unconditional, as in upstream CMake.
Separate Draw-off and native packages remain unaccepted. Installed STEP
geometry, Draw display behavior and a separate remove/reinstall lifecycle
remain acceptance work.
Focused source and runtime checks retain their separate boundaries in
[the analysis](../../../probes/kicad/occt/analysis.md).
