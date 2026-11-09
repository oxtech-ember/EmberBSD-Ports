# dxflib provenance and KiCad compatibility

[Upstream QCAD](https://qcad.org/en/90-dxflib) lists dxflib 3.26.4 and licenses it as GPLv2 or later.
The recipe fetches Debian's original-source mirror at
`https://deb.debian.org/debian/pool/main/d/dxflib/`; its archive hash is pinned
in `distinfo`. No C/C++ source is copied into Ports.

KiCad 10.0.8's vendored tree identifies as dxflib 3.17.0. Its source has
formatting and override annotations, plus these behavior/API differences from
3.26.4:

- The KiCad constructor initializes auxiliary parser state; this repair is
  carried as a patch to the common 3.26.4 source.
- The KiCad writer uses bounded `snprintf` and returns before dereferencing a
  null C string; both fixes are retained.
- The KiCad Windows compatibility macro checks whether `strcasecmp` already
  exists; the guarded definition is retained.
- KiCad opens Unicode filenames with `wxFopen` and calls `DL_Dxf::in(FILE*)`.
  The common provider carries this overload: a non-null stream is owned and
  closed on success, I/O error or callback exception. A null stream or I/O
  failure returns `false`; callback exceptions propagate. The existing path
  overload delegates to it. FILE and borrowed-stream entry points share a
  scoped temporary process-wide C locale, with restoration during exception
  unwinding. A borrowed stream remains caller-owned; non-EOF stream failures
  terminate with `false`, while configured stream exceptions propagate.
  Concurrent locale changes are not made safe by this patch.
- KiCad preserves POINT thickness (group 39) and POLYLINE VERTEX start/end
  widths (groups 40/41). The common entity structs and parser carry those
  fields, defaulting to zero when absent. Existing LWPOLYLINE callbacks retain
  their previous zero widths; this patch does not add a new lightweight
  polyline width interpretation or change writer output.
- KiCad adds optional `writeDimLinear` parameters and narrows the return types
  of `writeImage` and `writeDictionaryEntry`; current application sources do
  not call these APIs. Upstream's wider return types are kept.

The recipe exports the shared `dxflib::dxflib` CMake target and installs the
upstream public headers and GPL license text.

The extended public entity layouts require an ABI transition. The source and
package version remain 3.26.4; package revision 1 uses library ABI 4
(`SOVERSION 4`, library version 4.0.0), with API and ABI buildlink floors at
3.26.4nb1. Rebuild and relink existing consumers; an ABI 3 library must not be
substituted for ABI 4. KiCad is the current consumer in the shared Ports tree.

`tests/parser-contract.cpp` exercises the installed shared provider through
the exported CMake target. Configure the test directory with the selected SDK
C++ compiler and `CMAKE_PREFIX_PATH` pointing at that provider, build, then run
CTest. Cross-built tests run on the target using a writable directory argument.
The test verifies actual parsed field values and zero defaults, FILE closure,
Unicode filenames on POSIX, borrowed streams, read-error termination, and
file/locale cleanup when callbacks or stream reads throw. It does not claim
Windows Unicode path acceptance or complete KiCad graphical import acceptance.

The isolated Darwin arm64 shared-library build and installed CMake consumer
pass with the selected Ports Clang 23.1.4 and ld64.lld. The same parser fixture
passes host ASan/UBSan with leak detection and fatal sanitizer errors; this is
not target memory instrumentation or Valgrind acceptance. Target package
installation and KiCad import runtime remain separate checks.

Static analysis retains explicit limits: provider Cppcheck reports the same
101 warnings as the prior recipe (including Spline/Dimension/Hatch fields and
upstream self-test allocations). Provider CSA retains seven prior findings;
the failed-read stream warning is removed. Fixture CSA is clean. Cppcheck
misclassifies the fixture's conditional failure helper around `fopen`/`fwrite`
as a returning null/resource-release path; the helper exits on failure and
does not release the FILE on success. No diagnostic category is suppressed.
