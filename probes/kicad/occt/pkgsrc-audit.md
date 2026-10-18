# OCCT 8.0.1 package migration

The canonical pkgsrc provider is `cad/occt`, with package name `occt`.
KiCad includes that provider's `buildlink3.mk`. The common update must replace
that recipe and set its API and ABI dependency floor to 8.0.1.
It must not introduce a parallel `graphics/opencascade` installation.

## Existing patch audit

This audit compares the 15 `cad/occt` patches at pkgsrc commit
`fff4deb639a1a640476203c80f752fb77b6cb14b` with official OCCT 8.0.1.
The common profile targets EmberBSD/NetBSD, with Linux and Darwin build hosts.
It does not claim a SunOS port.

| Prior patch | OCCT 8.0.1 disposition |
| --- | --- |
| `patch-CMakeLists.txt` | Upstream already installs Draw scripts without group/world write permission. CMake 4.4.4 supports upstream's 3.10 minimum. Retain package-local `custom.sh` regeneration. Retire the explicit `DESTDIR` prefix in `file(INSTALL)`: current CMake already applies it. |
| `patch-adm_cmake_occt__macros.cmake` | Upstream target-file glob already includes `DESTDIR`. |
| `patch-adm_cmake_occt_csf.cmake` | Retain `${CMAKE_DL_LIBS}` through `netbsd-runtime.patch`. |
| `patch-src_MeshVS_MeshVS__MeshPrsBuilder.cxx` | SunOS-only `alloca.h` adaptation. Not carried for the common profile targets. |
| `patch-src_OSD_OSD__MemInfo.cxx` | Retain Linux-only `malloc.h` and portable `stdlib.h`. |
| `patch-src_OSD_OSD__Path.cxx` | Retain NetBSD Unix-path selection; also initialize the UNC flag. |
| `patch-src_OSD_OSD__signal.cxx` | SunOS signal constants and libsunmath handling. No SunOS acceptance is claimed. |
| `patch-src_OpenGl_OpenGl__ShaderObject.cxx` | SunOS-only `alloca.h` adaptation. Not needed on the common profile targets. |
| `patch-src_OpenGl_OpenGl__ShaderProgram.cxx` | Same SunOS-only header adaptation. |
| `patch-src_Standard_Standard__CString.cxx` | Replace the old diagnostic bypass with real NetBSD explicit-locale APIs. Do not suppress the unsupported-platform diagnostic. |
| `patch-src_Standard_Standard__Failure.cxx` | SunOS-only `alloca.h` adaptation. A separate actual-source regression repairs trace-size arithmetic before multiplication. |
| `patch-src_Standard_Standard__PrimitiveTypes.hxx` | Upstream removed this header. Do not restore its obsolete register-macro workaround. |
| `patch-src_Standard_Standard__StackTrace.cxx` | Replace the NetBSD no-operation branch with base `libexecinfo` support and checked heap frame storage. No Unix `alloca` remains in this path. |
| `patch-src_StdPrs_StdPrs__BRepFont.cxx` | Upstream uses `const auto*` for FreeType outline tags. The old cast is unnecessary. |
| `patch-src_ViewerTest_ViewerTest__CmdParser.cxx` | The old compiler workaround is unnecessary with GCC16 and the upstream C++17 implementation. |

The `check-install.rb` contract executes the actual upstream CMake fragments
and configuration macro. It reproduces an omitted `custom.sh` when an existing
prefix already contains the matching call. The repaired source installs it
without changing that prefix. The same test checks the compile-definitions
file under exactly one `DESTDIR` prefix. Adding `DESTDIR` again to `file(INSTALL)`
was rejected by an independent CMake 4.4.4 regression before publication.

## Normal package boundary

The full recipe must retain Foundation Classes, Modeling Data, Modeling
Algorithms, Visualization, Application Framework and Data Exchange.
Default `x11` and `occt-draw` options retain OpenGL, FreeImage and Tcl/Tk.
FreeType, fontconfig, Eigen and RapidJSON remain enabled. Release exception
and range checks stay enabled. Common dependencies supply their own headers
and libraries; OCCT must not download or install private replacements.

The shared Eigen provider needs 5.0.1. OCCT's manual Eigen discovery searches
`include/eigen3` and uses versionless `find_package(Eigen3 QUIET)` as a fallback.
It does not require a fake Eigen 3 version. FreeImage 3.19.25 is the maintained
fork selected for the common dependency update. Its codec coverage and system
library integration require their own checks. Tcl/Tk 9.1.0 is the current
stable release. The 8.6.18 maintenance page says development ends in 2026;
it is not described here as LTS.

The full package's static `PLIST` must come from the actual complete installed
stage and then pass ordinary pkgsrc checks. The old 7.8 header inventory is
not an 8.0.1 inventory. Source preparation and a private recipe draft do not
establish an accepted common package.

After installation, the independent Examples STEP reader must verify component
and assembly solids, closed shells, volume, bounds and mesh triangles through
the installed C++ API. TKernel/TKMath checks do not satisfy this requirement.
