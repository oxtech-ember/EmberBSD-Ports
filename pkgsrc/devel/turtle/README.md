# Turtle provider provenance

This recipe packages the current upstream release, `mat007/turtle` v2.0.0
(commit `2a54301cc3c5bb48c850913e15a6264f8140e86d`), under the Boost Software
License 1.0. KiCad's vendored headers match the upstream release except for
`version.hpp`, which is generated from the CMake project version.

The package installs upstream headers and CMake's `turtle::turtle` interface
target. The release archive still declares project version 1.3.2 in its
CMakeLists; the small carried patch corrects generated version metadata to
2.0.0. Boost headers are an interface dependency. Consumers should select
this package only for QA/test builds; it is not a normal SDK root.
