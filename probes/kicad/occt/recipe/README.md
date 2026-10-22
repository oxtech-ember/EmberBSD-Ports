# OCCT canonical recipe candidate

This AI-assisted source checkpoint prepares the existing `cad/occt` provider
for official OCCT 8.0.1. It has no `PLIST` and is not registered in the common
exporter. It does not establish a built or installed OCCT package.

The default recipe enables Foundation Classes, Modeling Data, Modeling Algorithms,
Visualization, Application Framework, Data Exchange and Draw. It retains shared
libraries, OpenGL/Xlib, FreeType/fontconfig, FreeImage 3.19.25nb3, Eigen 5.0.1,
RapidJSON and Tcl/Tk 9.1. Release range and exception checks remain active.
FreeImage is independent of the Xlib option. Optional upstream features keep
their existing defaults; no new diagnostic or test exclusions are added.

The eight `patch-*` symlinks refer to the authoritative probe patches. These
names are required by pkgsrc's ordinary patch discovery. Copy the candidate
with symlinks dereferenced into an isolated pkgsrc source view when testing it;
do not replace the shared export or the tracked upstream submodule with a link.
The archive and patch checksums are recorded in `distinfo` and `../source.json`.
Native and target builds require the common GCC16 toolchain.
Native Bash handles build-time script replacement. The ordinary target Bash
package supplies the installed Draw launcher; it is a separate runtime role.

Before promotion to the common profile:

1. Use actual current common dependency recipes, including Tcl/Tk 9.1 and the
   FreeImage system-codec provider. Preflight both native tools and target
   dependencies; never run uncoordinated recursive package installations.
2. Configure and build the complete default feature set. Verify the requested
   module and dependency values in the real CMake cache and selected libraries.
3. Derive the static `PLIST` from the complete target stage, preserving the
   actual header, toolkit, resources, Draw scripts and CMake-package inventory.
   The old 7.8 inventory must not be substituted or copied forward.
4. Run ordinary package checks and installed C++ consumers, including the
   Examples STEP reader's solids, shell closure, volume, bounds and mesh checks.

The current checkpoint verifies pinned source preparation, expanded native
pkgsrc metadata, six genuine Draw/Tcl source units with native GCC16.2, and the
missing-Tk CMake failure. Complete linking, stage inventory, package lifecycle,
positive Tk discovery and target STEP execution remain pending.
